import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.url import URL
from app.schemas.url import URLCreate
from app.utils.short_code import generate_short_code


class URLService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_short_code(self, short_code: str) -> URL | None:
        """Get URL by short code."""
        result = await self.db.execute(
            select(URL).where(URL.short_code == short_code)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        url_data: URLCreate,
        user_id: uuid.UUID | None = None,
    ) -> URL:
        """Create a new shortened URL."""
        # Use custom alias or generate random code
        if url_data.custom_alias:
            short_code = url_data.custom_alias
        else:
            short_code = await self._generate_unique_code()

        url = URL(
            short_code=short_code,
            original_url=str(url_data.url),
            user_id=user_id,
            expires_at=url_data.expires_at,
        )
        self.db.add(url)
        await self.db.commit()
        await self.db.refresh(url)
        return url

    async def _generate_unique_code(self, max_attempts: int = 10) -> str:
        """Generate a unique short code."""
        for _ in range(max_attempts):
            code = generate_short_code()
            existing = await self.get_by_short_code(code)
            if not existing:
                return code
        raise ValueError("Could not generate unique short code")

    async def short_code_exists(self, short_code: str) -> bool:
        """Check if a short code already exists."""
        result = await self.get_by_short_code(short_code)
        return result is not None

    async def get_user_urls(
        self,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[URL], int]:
        """Get all URLs for a user."""
        # Get total count
        count_result = await self.db.execute(
            select(URL).where(URL.user_id == user_id)
        )
        total = len(count_result.scalars().all())

        # Get paginated results
        result = await self.db.execute(
            select(URL)
            .where(URL.user_id == user_id)
            .order_by(URL.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all(), total

    async def update(
        self,
        url: URL,
        expires_at: datetime | None = None,
        is_active: bool | None = None,
    ) -> URL:
        """Update a URL."""
        if expires_at is not None:
            url.expires_at = expires_at
        if is_active is not None:
            url.is_active = is_active
        await self.db.commit()
        await self.db.refresh(url)
        return url

    async def deactivate(self, url: URL) -> URL:
        """Deactivate a URL (soft delete)."""
        url.is_active = False
        await self.db.commit()
        await self.db.refresh(url)
        return url
