"""
Redis-backed quota service for per-user request and spend tracking.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

_KEY_PREFIX = "promptshield:quota"
_SECONDS_IN_DAY = 86400


def _day_key(user_id: str, metric: str) -> str:
    """Build a daily TTL key for a user metric."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"{_KEY_PREFIX}:{user_id}:{metric}:{today}"


class QuotaService:
    """
    Manages per-user daily request and spend counters using Redis.

    Keys are namespaced by date, ensuring automatic daily reset via TTL.
    """

    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._redis = redis_client

    async def increment_request_count(self, user_id: str) -> int:
        """
        Increment the daily request counter for a user.

        Returns:
            The new counter value after incrementing.
        """
        key = _day_key(user_id, "requests")
        try:
            count = await self._redis.incr(key)
            await self._redis.expire(key, _SECONDS_IN_DAY)
            return int(count)
        except Exception as e:
            logger.warning("QuotaService.increment_request_count failed: %s", e)
            return 0

    async def increment_spend(self, user_id: str, amount_usd: float) -> float:
        """
        Increment the daily spend counter for a user.

        Returns:
            The new spend total after incrementing.
        """
        key = _day_key(user_id, "spend_usd")
        try:
            # Store as integer micro-dollars to avoid float precision issues
            micro_amount = int(amount_usd * 1_000_000)
            new_val = await self._redis.incrby(key, micro_amount)
            await self._redis.expire(key, _SECONDS_IN_DAY)
            return new_val / 1_000_000
        except Exception as e:
            logger.warning("QuotaService.increment_spend failed: %s", e)
            return 0.0

    async def get_daily_count(self, user_id: str) -> int:
        """Return the current daily request count for a user."""
        key = _day_key(user_id, "requests")
        try:
            val = await self._redis.get(key)
            return int(val) if val else 0
        except Exception as e:
            logger.warning("QuotaService.get_daily_count failed: %s", e)
            return 0

    async def get_daily_spend(self, user_id: str) -> float:
        """Return the current daily spend total for a user."""
        key = _day_key(user_id, "spend_usd")
        try:
            val = await self._redis.get(key)
            return int(val) / 1_000_000 if val else 0.0
        except Exception as e:
            logger.warning("QuotaService.get_daily_spend failed: %s", e)
            return 0.0

    async def check_quota(
        self,
        user_id: str,
        max_daily_requests: int | None,
        max_daily_spend_usd: float | None,
    ) -> tuple[bool, str | None]:
        """
        Check whether a user is within their daily quota limits.

        Args:
            user_id:             The user identifier.
            max_daily_requests:  Maximum allowed requests per day (None = unlimited).
            max_daily_spend_usd: Maximum allowed spend per day (None = unlimited).

        Returns:
            Tuple of (is_within_quota: bool, violated_rule: str | None).
        """
        if max_daily_requests is not None:
            count = await self.get_daily_count(user_id)
            if count >= max_daily_requests:
                return False, "daily_request_limit"

        if max_daily_spend_usd is not None:
            spend = await self.get_daily_spend(user_id)
            if spend >= max_daily_spend_usd:
                return False, "daily_spend_limit"

        return True, None

    async def reset_user(self, user_id: str) -> None:
        """Delete all quota keys for a user (admin use)."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        pattern = f"{_KEY_PREFIX}:{user_id}:*:{today}"
        try:
            keys = await self._redis.keys(pattern)
            if keys:
                await self._redis.delete(*keys)
        except Exception as e:
            logger.warning("QuotaService.reset_user failed: %s", e)
