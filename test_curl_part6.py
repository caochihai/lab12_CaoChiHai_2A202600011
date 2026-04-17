#!/usr/bin/env python3
import argparse
import json
import sys
import urllib.error
import urllib.request


def send_request(method, url, headers=None, body=None, timeout=10):
    payload = None
    req_headers = headers or {}
    if body is not None:
        payload = json.dumps(body).encode("utf-8")
        req_headers = {**req_headers, "Content-Type": "application/json"}

    req = urllib.request.Request(url=url, data=payload, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read().decode("utf-8", errors="replace")
            return resp.status, data
    except urllib.error.HTTPError as e:
        data = e.read().decode("utf-8", errors="replace")
        return e.code, data
    except Exception as e:
        return None, str(e)


def print_result(name, status, body, expected=None):
    if status is None:
        print(f"[ERROR] {name}: {body}")
        return False

    if expected is None:
        ok = True
    elif isinstance(expected, (list, tuple, set)):
        ok = status in expected
    else:
        ok = status == expected

    tag = "PASS" if ok else "FAIL"
    print(f"[{tag}] {name}: HTTP {status}")
    if body:
        print(f"  -> {body[:300]}")
    return ok


def main():
    parser = argparse.ArgumentParser(description="Batch test Day12 Part 6 API endpoints.")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--api-key", default="dev-key-change-me", help="X-API-Key value")
    parser.add_argument("--user-id", default="u1", help="User ID for ask/history tests")
    parser.add_argument("--rate-count", type=int, default=15, help="Number of requests for rate-limit test")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    total = 0
    passed = 0

    tests = []

    status, body = send_request("GET", f"{base}/health")
    tests.append(print_result("Health check", status, body, expected=200))

    status, body = send_request("GET", f"{base}/ready")
    tests.append(print_result("Readiness check", status, body, expected=200))

    status, body = send_request(
        "POST",
        f"{base}/ask",
        body={"user_id": args.user_id, "question": "Hello (no key)"},
    )
    tests.append(print_result("Ask without API key", status, body, expected=401))

    status, body = send_request(
        "POST",
        f"{base}/ask",
        headers={"X-API-Key": args.api_key},
        body={"user_id": args.user_id, "question": "Hello with key"},
    )
    tests.append(print_result("Ask with API key", status, body, expected=200))

    status, body = send_request(
        "GET",
        f"{base}/history/{args.user_id}",
        headers={"X-API-Key": args.api_key},
    )
    tests.append(print_result("History endpoint", status, body, expected=200))

    print("\n[INFO] Rate limit test...")
    rate_statuses = []
    for i in range(1, args.rate_count + 1):
        status, _ = send_request(
            "POST",
            f"{base}/ask",
            headers={"X-API-Key": args.api_key},
            body={"user_id": args.user_id, "question": f"rate test {i}"},
        )
        rate_statuses.append(status)

    has_429 = 429 in rate_statuses
    print(f"[{'PASS' if has_429 else 'FAIL'}] Rate limit: statuses={rate_statuses}")
    tests.append(has_429)

    total = len(tests)
    passed = sum(1 for x in tests if x)
    print(f"\nSummary: {passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
