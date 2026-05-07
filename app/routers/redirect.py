from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_url_service, get_cache_service, rate_limit_default
from app.services.url_service import URLService
from app.services.cache_service import CacheService
from app.services.click_service import ClickService
from app.services.rate_limit_service import RateLimitResult

router = APIRouter(tags=["redirect"])


async def log_click(
    db: AsyncSession,
    url_id: str,
    referrer: str | None,
    user_agent: str | None,
    ip_address: str | None,
):
    """Background task to log click."""
    click_service = ClickService(db)
    await click_service.record_click(
        url_id=url_id,
        referrer=referrer,
        user_agent=user_agent,
        ip_address=ip_address,
    )


@router.get("/{short_code}")
async def redirect_to_url(
    short_code: str,
    request: Request,
    background_tasks: BackgroundTasks,
    url_service: Annotated[URLService, Depends(get_url_service)],
    cache_service: Annotated[CacheService, Depends(get_cache_service)],
    db: Annotated[AsyncSession, Depends(get_db)],
    _rate_limit: Annotated[RateLimitResult, Depends(rate_limit_default)],
):
    """Redirect to the original URL."""
    # Try cache first
    cached = await cache_service.get_url(short_code)
    
    if cached:
        if not cached["is_active"]:
            raise HTTPException(status_code=410, detail="URL has been deactivated")
        original_url = cached["original_url"]
        # We need to fetch URL ID for click tracking
        url = await url_service.get_by_short_code(short_code)
        url_id = url.id if url else None
    else:
        # Cache miss - fetch from DB
        url = await url_service.get_by_short_code(short_code)
        
        if not url:
            raise HTTPException(status_code=404, detail="URL not found")
        
        if not url.is_active:
            raise HTTPException(status_code=410, detail="URL has been deactivated")
        
        # Check expiration
        if url.expires_at and url.expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=410, detail="URL has expired")
        
        original_url = url.original_url
        url_id = url.id
        
        # Cache the URL
        await cache_service.set_url(short_code, original_url, url.is_active)
    
    # Log click in background (don't block redirect)
    if url_id:
        background_tasks.add_task(
            log_click,
            db,
            url_id,
            request.headers.get("referer"),
            request.headers.get("user-agent"),
            request.client.host if request.client else None,
        )
    
    return RedirectResponse(url=original_url, status_code=302)
