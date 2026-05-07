import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.main import app
from app.database import Base, get_db
from app.dependencies import get_cache_service, get_rate_limit_service
from app.services.cache_service import CacheService
from app.services.rate_limit_service import RateLimitService, RateLimitResult
from app.config import get_settings

settings = get_settings()

# Use SQLite for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
test_session_maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with test_session_maker() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


class MockCacheService:
    """Mock cache service for testing."""
    def __init__(self):
        self._cache = {}

    async def get_url(self, short_code: str):
        return self._cache.get(short_code)

    async def set_url(self, short_code: str, original_url: str, is_active: bool = True):
        self._cache[short_code] = {"original_url": original_url, "is_active": is_active}

    async def delete_url(self, short_code: str):
        self._cache.pop(short_code, None)

    async def invalidate_url(self, short_code: str):
        await self.delete_url(short_code)


class MockRateLimitService:
    """Mock rate limit service for testing - always allows requests."""

    async def check_rate_limit(
        self,
        key: str,
        limit: int | None = None,
        window_seconds: int | None = None,
    ) -> RateLimitResult:
        return RateLimitResult(
            allowed=True,
            limit=limit or 60,
            remaining=59,
            reset_at=9999999999,
        )

    async def get_remaining(self, key: str, limit: int | None = None) -> int:
        return limit or 60


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    async def override_get_cache_service():
        return MockCacheService()

    async def override_get_rate_limit_service():
        return MockRateLimitService()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_cache_service] = override_get_cache_service
    app.dependency_overrides[get_rate_limit_service] = override_get_rate_limit_service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
