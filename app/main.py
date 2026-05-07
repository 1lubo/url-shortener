from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.redis import init_redis, close_redis
from app.routers import urls, auth, redirect, ui

settings = get_settings()


class RateLimitHeaderMiddleware(BaseHTTPMiddleware):
    """Add rate limit headers to responses."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        # Add rate limit headers if available in request state
        if hasattr(request.state, "rate_limit"):
            rl = request.state.rate_limit
            response.headers["X-RateLimit-Limit"] = str(rl.limit)
            response.headers["X-RateLimit-Remaining"] = str(rl.remaining)
            response.headers["X-RateLimit-Reset"] = str(rl.reset_at)

        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_redis()
    yield
    # Shutdown
    await close_redis()


app = FastAPI(
    title=settings.app_name,
    description="A URL shortening service with Redis caching and click analytics",
    version="1.0.0",
    lifespan=lifespan,
)

# Add rate limit header middleware
app.add_middleware(RateLimitHeaderMiddleware)

@app.get("/health")
async def health_check():
    """Health check endpoint for Fly.io."""
    return {"status": "healthy"}


# Include routers
# UI router first for / and /shorten routes
app.include_router(ui.router)
app.include_router(auth.router)
app.include_router(urls.router)
# Redirect router must be last since it has catch-all /{short_code}
app.include_router(redirect.router)
