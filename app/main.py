from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.redis import init_redis, close_redis
from app.routers import urls, auth, redirect

settings = get_settings()


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

@app.get("/health")
async def health_check():
    """Health check endpoint for Fly.io."""
    return {"status": "healthy"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "docs": "/docs",
        "health": "/health",
    }


# Include routers - redirect router must be last since it has catch-all /{short_code}
app.include_router(auth.router)
app.include_router(urls.router)
app.include_router(redirect.router)
