import hashlib
import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.click import Click
from app.models.url import URL


class ClickService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def hash_ip(ip: str) -> str:
        """Hash IP address for privacy."""
        return hashlib.sha256(ip.encode()).hexdigest()[:16]

    async def record_click(
        self,
        url_id: uuid.UUID,
        referrer: str | None = None,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> Click:
        """Record a click event."""
        click = Click(
            url_id=url_id,
            referrer=referrer,
            user_agent=user_agent,
            ip_hash=self.hash_ip(ip_address) if ip_address else None,
        )
        self.db.add(click)
        await self.db.commit()
        return click

    async def get_click_count(self, url_id: uuid.UUID) -> int:
        """Get total click count for a URL."""
        result = await self.db.execute(
            select(func.count(Click.id)).where(Click.url_id == url_id)
        )
        return result.scalar() or 0

    async def get_recent_clicks(
        self,
        url_id: uuid.UUID,
        limit: int = 10,
    ) -> list[Click]:
        """Get recent clicks for a URL."""
        result = await self.db.execute(
            select(Click)
            .where(Click.url_id == url_id)
            .order_by(Click.clicked_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_clicks_by_date(
        self,
        url_id: uuid.UUID,
    ) -> list[tuple[str, int]]:
        """Get click counts grouped by date."""
        result = await self.db.execute(
            select(
                func.date(Click.clicked_at).label("date"),
                func.count(Click.id).label("count"),
            )
            .where(Click.url_id == url_id)
            .group_by(func.date(Click.clicked_at))
            .order_by(func.date(Click.clicked_at).desc())
            .limit(30)
        )
        return [(str(row.date), row.count) for row in result.all()]

    async def get_top_referrers(
        self,
        url_id: uuid.UUID,
        limit: int = 10,
    ) -> list[tuple[str, int]]:
        """Get top referrers for a URL."""
        result = await self.db.execute(
            select(
                Click.referrer,
                func.count(Click.id).label("count"),
            )
            .where(Click.url_id == url_id)
            .where(Click.referrer.isnot(None))
            .group_by(Click.referrer)
            .order_by(func.count(Click.id).desc())
            .limit(limit)
        )
        return [(row.referrer, row.count) for row in result.all()]
