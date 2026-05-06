from datetime import datetime

from pydantic import BaseModel


class ClickInfo(BaseModel):
    clicked_at: datetime
    referrer: str | None
    user_agent: str | None

    class Config:
        from_attributes = True


class URLStats(BaseModel):
    short_code: str
    original_url: str
    total_clicks: int
    created_at: datetime
    recent_clicks: list[ClickInfo]


class ClicksByDate(BaseModel):
    date: str
    count: int


class DetailedStats(BaseModel):
    short_code: str
    original_url: str
    total_clicks: int
    created_at: datetime
    clicks_by_date: list[ClicksByDate]
    top_referrers: list[tuple[str, int]]
    recent_clicks: list[ClickInfo]
