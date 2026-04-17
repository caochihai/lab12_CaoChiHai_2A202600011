"""Final project: production-ready AI agent for Day 12 Part 6."""
import json
import logging
import os
import signal
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import redis
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import cost_guard
from app.rate_limiter import rate_limiter
from utils.mock_llm import ask as llm_ask

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format='{"ts":"%(asctime)s","lvl":"%(levelname)s","msg":"%(message)s"}',
)
logger = logging.getLogger(__name__)

START_TIME = time.time()
_is_ready = False
_is_shutting_down = False
_in_flight = 0
_request_count = 0
_error_count = 0

redis_client = redis.from_url(settings.redis_url, decode_responses=True)


class AskRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    question: str = Field(..., min_length=1, max_length=2000)


class AskResponse(BaseModel):
    user_id: str
    question: str
    answer: str
    model: str
    history_count: int
    timestamp: str


def _history_key(user_id: str) -> str:
    return f"history:{user_id}"


def _append_history(user_id: str, role: str, content: str) -> None:
    item = json.dumps(
        {
            "role": role,
            "content": content,
            "ts": datetime.now(timezone.utc).isoformat(),
        }
    )
    key = _history_key(user_id)
    redis_client.rpush(key, item)
    # keep latest 20 messages (10 turns)
    redis_client.ltrim(key, -20, -1)
    redis_client.expire(key, 30 * 24 * 3600)


def _get_history(user_id: str) -> list[dict]:
    items = redis_client.lrange(_history_key(user_id), 0, -1)
    return [json.loads(x) for x in items]


@asynccontextmanager
async def lifespan(_: FastAPI):
    global _is_ready
    logger.info(json.dumps({"event": "startup", "env": settings.environment}))
    try:
        redis_client.ping()
    except redis.RedisError as exc:
        logger.error(json.dumps({"event": "redis_unavailable", "detail": str(exc)}))
        _is_ready = False
    else:
        _is_ready = True
        logger.info(json.dumps({"event": "ready"}))

    yield

    _is_ready = False
    logger.info(json.dumps({"event": "shutdown"}))


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)


@app.middleware("http")
async def middleware(request: Request, call_next):
    global _request_count, _error_count, _in_flight

    if _is_shutting_down and request.url.path not in ("/health", "/ready"):
        return Response(status_code=503, content="Server is shutting down")

    start = time.time()
    _request_count += 1
    _in_flight += 1
    try:
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if "server" in response.headers:
            del response.headers["server"]
        logger.info(
            json.dumps(
                {
                    "event": "request",
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "ms": round((time.time() - start) * 1000, 1),
                }
            )
        )
        return response
    except Exception:
        _error_count += 1
        raise
    finally:
        _in_flight -= 1


@app.get("/")
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "endpoints": {
            "ask": "POST /ask",
            "history": "GET /history/{user_id}",
            "health": "GET /health",
            "ready": "GET /ready",
        },
    }


@app.post("/ask", response_model=AskResponse)
async def ask_agent(body: AskRequest, _key: str = Depends(verify_api_key)):
    if not _is_ready:
        raise HTTPException(503, "Service not ready")

    # Authenticated key + user_id bucket
    rate_limiter.check(f"{_key[:8]}:{body.user_id}")

    user_prompt_tokens = len(body.question.split()) * 2
    cost_guard.check_and_record(body.user_id, input_tokens=user_prompt_tokens, output_tokens=0)

    _append_history(body.user_id, "user", body.question)
    answer = llm_ask(body.question)
    assistant_tokens = len(answer.split()) * 2
    cost_guard.check_and_record(body.user_id, input_tokens=0, output_tokens=assistant_tokens)
    _append_history(body.user_id, "assistant", answer)
    history = _get_history(body.user_id)

    return AskResponse(
        user_id=body.user_id,
        question=body.question,
        answer=answer,
        model=settings.llm_model,
        history_count=len(history),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/history/{user_id}")
def get_history(user_id: str, _key: str = Depends(verify_api_key)):
    return {"user_id": user_id, "messages": _get_history(user_id)}


@app.delete("/history/{user_id}")
def clear_history(user_id: str, _key: str = Depends(verify_api_key)):
    redis_client.delete(_history_key(user_id))
    return {"deleted": True, "user_id": user_id}


@app.get("/health")
def health():
    redis_ok = False
    try:
        redis_client.ping()
        redis_ok = True
    except redis.RedisError:
        redis_ok = False

    status = "ok" if redis_ok else "degraded"
    return {
        "status": status,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "requests": _request_count,
        "errors": _error_count,
        "redis": redis_ok,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready")
def ready():
    if not _is_ready or _is_shutting_down:
        raise HTTPException(503, "Not ready")
    try:
        redis_client.ping()
    except redis.RedisError as exc:
        raise HTTPException(503, "Redis unavailable") from exc
    return {"ready": True}


@app.get("/metrics")
def metrics(_key: str = Depends(verify_api_key)):
    return {
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "requests": _request_count,
        "errors": _error_count,
        "in_flight": _in_flight,
    }


def _handle_signal(signum, _frame):
    global _is_shutting_down, _is_ready
    if _is_shutting_down:
        return
    _is_shutting_down = True
    _is_ready = False
    logger.info(json.dumps({"event": "signal", "signum": signum, "action": "graceful_shutdown"}))


signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)


if __name__ == "__main__":
    logger.info(f"Starting {settings.app_name} on {settings.host}:{settings.port}")
    logger.info(f"API Key: {settings.agent_api_key[:4]}****")
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        timeout_graceful_shutdown=30,
    )
