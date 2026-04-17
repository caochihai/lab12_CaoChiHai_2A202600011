# Deployment Information

## Public URL
https://api-production-4cbb.up.railway.app

## Platform
Railway

## Last Verified
2026-04-17 23:00 ICT (Asia/Bangkok)

## Test Commands

### Health Check
```bash
curl https://api-production-4cbb.up.railway.app/health
# Expected: {"status":"ok", ...}
```

### Readiness Check
```bash
curl https://api-production-4cbb.up.railway.app/ready
# Expected: {"ready": true}
```

### Authentication Required (No API Key)
```bash
curl -X POST https://api-production-4cbb.up.railway.app/ask \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"Hello"}'
# Expected: 401 Unauthorized
```

### API Test (With Authentication)
```bash
curl -X POST https://api-production-4cbb.up.railway.app/ask \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"Hello"}'
# Expected: 200 OK
```

### Rate Limiting Test
```bash
for i in {1..15}; do
  curl -X POST https://api-production-4cbb.up.railway.app/ask \
    -H "X-API-Key: YOUR_KEY" \
    -H "Content-Type: application/json" \
    -d '{"user_id":"test","question":"rate test"}'
  echo
done
# Expected: eventually returns 429 Too Many Requests
```

## Test Results Summary

| Check | Expected | Latest Result | Status |
|---|---|---|---|
| `/health` | HTTP 200 | HTTP 200 (verified) | PASS |
| `/ready` | HTTP 200 | HTTP 200 (verified) | PASS |
| `/ask` without API key | HTTP 401 | HTTP 401 (verified) | PASS |
| `/ask` with API key | HTTP 200 | HTTP 200 (verified) | PASS |
| `/history/{user_id}` | HTTP 200 | HTTP 200 (verified) | PASS |
| Rate limiting | HTTP 429 after threshold | statuses include 429 after limit | PASS |

## Environment Variables Set
- `PORT=8000`
- `REDIS_URL` set in Railway project variables (secret hidden)
- `AGENT_API_KEY` set in Railway project variables (secret hidden)
- `LOG_LEVEL=INFO`

## Screenshots
- [Service running](screenshots/run_server.png)
- [Command/API test](screenshots/image_cmd.png)
- [Test results](screenshots/image_test.png)

## Notes
- Real secrets are not committed to git.
- If cloud deployment changes, rerun test commands and update this file.
