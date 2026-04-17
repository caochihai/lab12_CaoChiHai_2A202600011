# Deployment Information

## Public URL
https://api-production-4cbb.up.railway.app

## Platform
Railway

## Last Verified
2026-04-17 22:22 ICT (Asia/Bangkok)

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
| `/health` | HTTP 200 | HTTP 200 (local verified) | PASS |
| `/ready` | HTTP 200 | HTTP 200 (local verified) | PASS |
| `/ask` without API key | HTTP 401 | HTTP 401 (local verified) | PASS |
| `/ask` with API key | HTTP 200 | HTTP 200 (local verified) | PASS |
| `/history/{user_id}` | HTTP 200 | HTTP 200 (local verified) | PASS |
| Rate limiting | HTTP 429 after threshold | statuses: [200, 200, 200, 200, 200, 200, 200, 200, 200, 429, 429, 429, 429, 429, 429] (local verified) | PASS |

## Rate Limit Verification
- Current status: PASS (returns HTTP 429 after threshold).
- Verified with `test_curl_part6.py --rate-count 15` after rate-limiter fix and container rebuild.

## Environment Variables Set
- PORT=8000
- REDIS_URL=set in Railway project variables (secret hidden)
- AGENT_API_KEY=set in Railway project variables (secret hidden)
- LOG_LEVEL=INFO

## Screenshots
- [Deployment dashboard](screenshots/image.png)
- [Service running](screenshots/image_cmd.png)
- [Test results](screenshots/image_cmd.png)

## Notes
- Do not commit real secrets. Keep API keys only in Railway Variables.
- If cloud deployment is updated, rerun the same test commands against Public URL and refresh this section.
