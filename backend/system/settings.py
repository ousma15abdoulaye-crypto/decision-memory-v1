"""DMS system settings – loaded from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings

__all__ = ["Settings", "get_settings"]


class Settings(BaseSettings):
    """Application-wide configuration backed by env vars / .env file."""

    DATABASE_URL: str = "sqlite+aiosqlite:///./dms_dev.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480
    USE_LLM: bool = False
    LLM_PROVIDER: str = "openai"  # openai | claude
    OPENAI_API_KEY: str | None = None
    UPLOAD_DIR: str = "./uploads"
    OUTPUT_DIR: str = "./outputs"
    MAX_FILE_SIZE_MB: int = 50
    CELERY_THRESHOLD_MB: int = 3

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
