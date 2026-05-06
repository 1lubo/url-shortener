import json
from typing import Any

import redis.asyncio as redis

from app.config import get_settings

settings = get_settings()


class CacheService:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.ttl = settings.cache_ttl_seconds

    def _url_key(self, short_code: str) -> str:
        return f"url:{short_code}"

    async def get_url(self, short_code: str) -> dict[str, Any] | None:
        """Get cached URL data."""
        data = await self.redis.get(self._url_key(short_code))
        if data:
            return json.loads(data)
        return None

    async def set_url(
        self,
        short_code: str,
        original_url: str,
        is_active: bool = True,
    ) -> None:
        """Cache URL data."""
        data = json.dumps({
            "original_url": original_url,
            "is_active": is_active,
        })
        await self.redis.setex(
            self._url_key(short_code),
            self.ttl,
            data,
        )

    async def delete_url(self, short_code: str) -> None:
        """Remove URL from cache."""
        await self.redis.delete(self._url_key(short_code))

    async def invalidate_url(self, short_code: str) -> None:
        """Alias for delete_url - used when URL is updated."""
        await self.delete_url(short_code)
