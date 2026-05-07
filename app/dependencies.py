from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.redis import get_redis
from app.services.auth_service import AuthService, decode_token
from app.services.url_service import URLService
from app.services.cache_service import CacheService
from app.services.rate_limit_service import RateLimitService, RateLimitResult
from app.models.user import User

security = HTTPBearer(auto_error=False)


async def get_url_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> URLService:
    return URLService(db)


async def get_cache_service() -> CacheService:
    return CacheService(get_redis())


async def get_rate_limit_service() -> RateLimitService:
    return RateLimitService(get_redis())


def get_client_ip(request: Request) -> str:
    """Extract client IP from request, handling proxies."""
    # Check X-Forwarded-For header (set by proxies/load balancers)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP (original client)
        return forwarded_for.split(",")[0].strip()

    # Check X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Fall back to direct client IP
    return request.client.host if request.client else "unknown"


def create_rate_limit_dependency(
    limit: int | None = None,
    window_seconds: int | None = None,
    key_prefix: str = "ip",
):
    """
    Factory function to create rate limit dependencies with custom limits.

    Usage:
        @router.post("/urls")
        async def create_url(
            _: Annotated[RateLimitResult, Depends(create_rate_limit_dependency(limit=10))],
        ):
            ...
    """

    async def rate_limit_dependency(
        request: Request,
        rate_limit_service: Annotated[RateLimitService, Depends(get_rate_limit_service)],
    ) -> RateLimitResult:
        client_ip = get_client_ip(request)
        key = f"{key_prefix}:{client_ip}"

        result = await rate_limit_service.check_rate_limit(
            key=key,
            limit=limit,
            window_seconds=window_seconds,
        )

        # Store result in request state for response headers
        request.state.rate_limit = result

        if not result.allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
                headers={
                    "X-RateLimit-Limit": str(result.limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(result.reset_at),
                    "Retry-After": str(result.reset_at),
                },
            )

        return result

    return rate_limit_dependency


# Pre-configured rate limiters for common use cases
rate_limit_default = create_rate_limit_dependency()
rate_limit_strict = create_rate_limit_dependency(limit=10, window_seconds=60)
rate_limit_auth = create_rate_limit_dependency(limit=5, window_seconds=60, key_prefix="auth")


async def get_auth_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthService:
    return AuthService(db)


async def get_current_user_optional(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> User | None:
    """Get current user if authenticated, otherwise return None."""
    if not credentials:
        return None
    
    token_data = decode_token(credentials.credentials)
    if not token_data or not token_data.user_id:
        return None
    
    return await auth_service.get_user_by_id(token_data.user_id)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    """Get current user, raise 401 if not authenticated."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    
    token_data = decode_token(credentials.credentials)
    if not token_data or not token_data.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    
    user = await auth_service.get_user_by_id(token_data.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    return user
