from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, HttpUrl, Field


class URLCreate(BaseModel):
    url: HttpUrl
    custom_alias: str | None = Field(
        default=None,
        min_length=3,
        max_length=20,
        pattern=r"^[a-zA-Z0-9_-]+$",
    )
    expires_at: datetime | None = None


class URLResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    short_code: str
    short_url: str
    original_url: str
    created_at: datetime
    expires_at: datetime | None = None
    is_active: bool


class URLUpdate(BaseModel):
    expires_at: datetime | None = None
    is_active: bool | None = None


class URLListResponse(BaseModel):
    urls: list[URLResponse]
    total: int
