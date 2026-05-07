from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.dependencies import (
    get_url_service,
    get_cache_service,
    get_current_user,
    get_current_user_optional,
    rate_limit_strict,
)
from app.services.rate_limit_service import RateLimitResult
from app.models.user import User
from app.schemas.url import URLCreate, URLResponse, URLUpdate, URLListResponse
from app.schemas.stats import URLStats, ClickInfo
from app.services.url_service import URLService
from app.services.cache_service import CacheService
from app.services.click_service import ClickService
from app.services.qr_service import QRService

router = APIRouter(prefix="/api/v1/urls", tags=["urls"])
settings = get_settings()


@router.post("", response_model=URLResponse, status_code=status.HTTP_201_CREATED)
async def create_short_url(
    url_data: URLCreate,
    url_service: Annotated[URLService, Depends(get_url_service)],
    current_user: Annotated[User | None, Depends(get_current_user_optional)],
    _rate_limit: Annotated[RateLimitResult, Depends(rate_limit_strict)],
):
    """Create a new shortened URL."""
    # Check if custom alias is already taken
    if url_data.custom_alias:
        if await url_service.short_code_exists(url_data.custom_alias):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Custom alias already exists",
            )

    user_id = current_user.id if current_user else None
    url = await url_service.create(url_data, user_id)

    return URLResponse(
        id=url.id,
        short_code=url.short_code,
        short_url=f"{settings.base_url}/{url.short_code}",
        original_url=url.original_url,
        created_at=url.created_at,
        expires_at=url.expires_at,
        is_active=url.is_active,
    )


@router.get("", response_model=URLListResponse)
async def list_user_urls(
    url_service: Annotated[URLService, Depends(get_url_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = 0,
    limit: int = 50,
):
    """List all URLs created by the authenticated user."""
    urls, total = await url_service.get_user_urls(current_user.id, skip, limit)
    return URLListResponse(
        urls=[
            URLResponse(
                id=url.id,
                short_code=url.short_code,
                short_url=f"{settings.base_url}/{url.short_code}",
                original_url=url.original_url,
                created_at=url.created_at,
                expires_at=url.expires_at,
                is_active=url.is_active,
            )
            for url in urls
        ],
        total=total,
    )


@router.patch("/{short_code}", response_model=URLResponse)
async def update_url(
    short_code: str,
    url_update: URLUpdate,
    url_service: Annotated[URLService, Depends(get_url_service)],
    cache_service: Annotated[CacheService, Depends(get_cache_service)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Update a URL (owner only)."""
    url = await url_service.get_by_short_code(short_code)
    if not url:
        raise HTTPException(status_code=404, detail="URL not found")
    if url.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    url = await url_service.update(
        url,
        expires_at=url_update.expires_at,
        is_active=url_update.is_active,
    )
    
    # Invalidate cache
    await cache_service.invalidate_url(short_code)

    return URLResponse(
        id=url.id,
        short_code=url.short_code,
        short_url=f"{settings.base_url}/{url.short_code}",
        original_url=url.original_url,
        created_at=url.created_at,
        expires_at=url.expires_at,
        is_active=url.is_active,
    )


@router.delete("/{short_code}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_url(
    short_code: str,
    url_service: Annotated[URLService, Depends(get_url_service)],
    cache_service: Annotated[CacheService, Depends(get_cache_service)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Deactivate a URL (owner only)."""
    url = await url_service.get_by_short_code(short_code)
    if not url:
        raise HTTPException(status_code=404, detail="URL not found")
    if url.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    await url_service.deactivate(url)
    await cache_service.invalidate_url(short_code)


@router.get("/{short_code}/stats", response_model=URLStats)
async def get_url_stats(
    short_code: str,
    url_service: Annotated[URLService, Depends(get_url_service)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get click statistics for a URL."""
    url = await url_service.get_by_short_code(short_code)
    if not url:
        raise HTTPException(status_code=404, detail="URL not found")

    click_service = ClickService(db)
    total_clicks = await click_service.get_click_count(url.id)
    recent_clicks = await click_service.get_recent_clicks(url.id, limit=10)

    return URLStats(
        short_code=url.short_code,
        original_url=url.original_url,
        total_clicks=total_clicks,
        created_at=url.created_at,
        recent_clicks=[
            ClickInfo(
                clicked_at=click.clicked_at,
                referrer=click.referrer,
                user_agent=click.user_agent,
            )
            for click in recent_clicks
        ],
    )


@router.get("/{short_code}/qr")
async def get_qr_code(
    short_code: str,
    url_service: Annotated[URLService, Depends(get_url_service)],
    size: int = 10,
):
    """
    Generate a QR code PNG image for a shortened URL.

    Args:
        short_code: The short code of the URL
        size: QR code size (pixels per module), default 10, range 5-20
    """
    url = await url_service.get_by_short_code(short_code)
    if not url:
        raise HTTPException(status_code=404, detail="URL not found")
    if not url.is_active:
        raise HTTPException(status_code=410, detail="URL has been deactivated")

    # Clamp size to reasonable range
    size = max(5, min(20, size))

    short_url = f"{settings.base_url}/{short_code}"
    qr_bytes = QRService.generate_qr_code(short_url, size=size)

    return Response(
        content=qr_bytes,
        media_type="image/png",
        headers={
            "Content-Disposition": f'inline; filename="{short_code}-qr.png"',
            "Cache-Control": "public, max-age=86400",  # Cache for 1 day
        },
    )
