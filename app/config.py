from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # App
    app_name: str = "URL Shortener"
    base_url: str = "http://localhost:8000"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/urlshortener"

    # Redis
    redis_url: str = "redis://localhost:6379"
    cache_ttl_seconds: int = 3600  # 1 hour

    # JWT
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Short code settings
    short_code_length: int = 6

    # Rate limiting (requests per window)
    rate_limit_requests: int = 60  # requests allowed per window
    rate_limit_window_seconds: int = 60  # window size in seconds
    rate_limit_burst: int = 10  # extra burst capacity for short spikes


@lru_cache
def get_settings() -> Settings:
    return Settings()
