import time
from dataclasses import dataclass

import redis.asyncio as redis

from app.config import get_settings

settings = get_settings()


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""

    allowed: bool
    limit: int
    remaining: int
    reset_at: int  # Unix timestamp when the window resets


class RateLimitService:
    """
    Redis-based rate limiting using sliding window algorithm.
    
    Uses a sorted set to track request timestamps, allowing for
    accurate rate limiting that doesn't have the boundary issues
    of fixed windows.
    """

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def check_rate_limit(
        self,
        key: str,
        limit: int | None = None,
        window_seconds: int | None = None,
    ) -> RateLimitResult:
        """
        Check if a request is allowed under the rate limit.

        Args:
            key: Unique identifier (e.g., "ip:192.168.1.1" or "user:uuid")
            limit: Max requests per window (default from settings)
            window_seconds: Window size in seconds (default from settings)

        Returns:
            RateLimitResult with allowed status and metadata
        """
        limit = limit or settings.rate_limit_requests
        window_seconds = window_seconds or settings.rate_limit_window_seconds

        now = time.time()
        window_start = now - window_seconds
        redis_key = f"ratelimit:{key}"

        # Use a pipeline for atomic operations
        pipe = self.redis.pipeline()

        # Remove old entries outside the window
        pipe.zremrangebyscore(redis_key, 0, window_start)

        # Count current requests in window
        pipe.zcard(redis_key)

        # Add current request
        pipe.zadd(redis_key, {str(now): now})

        # Set expiry on the key
        pipe.expire(redis_key, window_seconds + 1)

        results = await pipe.execute()
        current_count = results[1]  # zcard result

        remaining = max(0, limit - current_count - 1)
        reset_at = int(now + window_seconds)

        if current_count >= limit:
            # Over limit - remove the request we just added
            await self.redis.zrem(redis_key, str(now))
            return RateLimitResult(
                allowed=False,
                limit=limit,
                remaining=0,
                reset_at=reset_at,
            )

        return RateLimitResult(
            allowed=True,
            limit=limit,
            remaining=remaining,
            reset_at=reset_at,
        )

    async def get_remaining(self, key: str, limit: int | None = None) -> int:
        """Get remaining requests for a key without consuming one."""
        limit = limit or settings.rate_limit_requests
        window_seconds = settings.rate_limit_window_seconds

        now = time.time()
        window_start = now - window_seconds
        redis_key = f"ratelimit:{key}"

        # Clean and count
        await self.redis.zremrangebyscore(redis_key, 0, window_start)
        current_count = await self.redis.zcard(redis_key)

        return max(0, limit - current_count)
