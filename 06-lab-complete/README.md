# Day 12 - Part 6 Final Project

Production-ready AI agent combining all Day 12 requirements.

## Included Features

- Config from environment variables (12-factor)
- API key authentication (`X-API-Key`)
- Rate limiting (`10 req/min` default)
- Monthly budget guard (`$10` default)
- Health (`/health`) and readiness (`/ready`)
- Graceful shutdown (SIGTERM/SIGINT)
- Stateless conversation history in Redis
- Docker multi-stage build + docker compose stack

## Project Structure

```text
06-lab-complete/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── auth.py
│   ├── rate_limiter.py
│   └── cost_guard.py
├── utils/
│   └── mock_llm.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .dockerignore
├── railway.toml
├── render.yaml
└── check_production_ready.py
```

## Quick Run (Docker - Recommended)

### Windows CMD

```bat
cd /d D:\lab12\day12_ha-tang-cloud_va_deployment\06-lab-complete
copy .env.example .env.local
docker compose up -d --build
curl http://localhost:8000/health
```

### Git Bash / macOS / Linux

```bash
cd /d/lab12/day12_ha-tang-cloud_va_deployment/06-lab-complete
cp .env.example .env.local
docker compose up -d --build
curl http://localhost:8000/health
```

## API Test

### 1) Without key -> 401

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u1","question":"Hello"}'
```

### 2) With key -> 200

```bash
curl -X POST http://localhost:8000/ask \
  -H "X-API-Key: dev-key-change-me" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u1","question":"Hello"}'
```

### 3) Read conversation history

```bash
curl -H "X-API-Key: dev-key-change-me" http://localhost:8000/history/u1
```

## Run Without Docker

```bash
cd 06-lab-complete
python -m pip install -r requirements.txt
# Start Redis separately, then:
set REDIS_URL=redis://localhost:6379/0   # CMD
python app/main.py
```

## Stop

```bash
docker compose down
```

## Optional Validation

```bash
python check_production_ready.py
```
