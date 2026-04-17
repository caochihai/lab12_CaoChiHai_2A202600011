"""Cost guard module: monthly per-user budget with Redis backing."""
from datetime import datetime

import redis
from fastapi import HTTPException

from app.config import settings


class CostGuard:
    def __init__(self) -> None:
        self._redis = redis.from_url(settings.redis_url, decode_responses=True)

    @staticmethod
    def estimate_cost_usd(input_tokens: int, output_tokens: int) -> float:
        # Mock pricing for lab purposes.
        return (input_tokens / 1000.0) * 0.00015 + (output_tokens / 1000.0) * 0.0006

    def _month_key(self, user_id: str) -> str:
        month = datetime.utcnow().strftime("%Y-%m")
        return f"budget:{user_id}:{month}"

    def check_and_record(self, user_id: str, input_tokens: int, output_tokens: int) -> float:
        add_cost = self.estimate_cost_usd(input_tokens, output_tokens)
        key = self._month_key(user_id)

        try:
            current = float(self._redis.get(key) or 0.0)
            if current + add_cost > settings.monthly_budget_usd:
                raise HTTPException(402, "Monthly budget exceeded")
            self._redis.incrbyfloat(key, add_cost)
            # Keep budget keys for roughly 40 days.
            self._redis.expire(key, 40 * 24 * 3600)
            return current + add_cost
        except redis.RedisError as exc:
            raise HTTPException(503, "Cost guard unavailable (Redis error)") from exc


cost_guard = CostGuard()
