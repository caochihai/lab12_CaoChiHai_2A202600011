"""Rate limiter module: sliding window with Redis backing."""
import time
import uuid
from collections import defaultdict, deque

import redis
from fastapi import HTTPException

from app.config import settings


class RateLimiter:
    def __init__(self) -> None:
        self._redis = redis.from_url(settings.redis_url, decode_responses=True)
        self._fallback = defaultdict(deque)

    def _key(self, user_id: str) -> str:
        return f"rate:{user_id}"

    def check(self, user_id: str) -> None:
        now = time.time()
        cutoff = now - 60
        limit = settings.rate_limit_per_minute

        try:
            key = self._key(user_id)
            # Each request needs a unique sorted-set member. If member uses
            # only second-level timestamp, requests in the same second overwrite
            # each other and the counter never reaches the limit.
            member = f"{now:.6f}:{uuid.uuid4().hex}"

            pipe = self._redis.pipeline()
            pipe.zremrangebyscore(key, 0, cutoff)
            pipe.zcard(key)
            _, count = pipe.execute()

            if count >= limit:
                raise HTTPException(429, f"Rate limit exceeded: {limit} req/min")

            pipe = self._redis.pipeline()
            pipe.zadd(key, {member: now})
            pipe.expire(key, 120)
            pipe.execute()
            return
        except redis.RedisError:
            # Fallback only for availability; production should keep Redis healthy.
            window = self._fallback[user_id]
            while window and window[0] < cutoff:
                window.popleft()
            if len(window) >= limit:
                raise HTTPException(429, f"Rate limit exceeded: {limit} req/min")
            window.append(now)


rate_limiter = RateLimiter()
