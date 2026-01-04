"""Application configuration and environment variable management."""

from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized application settings with environment variable support."""

    APP_NAME: str = "TradeMind"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, v):
        """Parse DEBUG field, handling string and boolean values."""
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            if v.lower() in ("true", "1", "yes", "on"):
                return True
            if v.lower() in ("false", "0", "no", "off", "warn", "info", "error"):
                return False
        return bool(v) if v else False

    API_V1_PREFIX: str = "/api/v1"

    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:8000",
    ]

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/trademind"
    DATABASE_ECHO: bool = False

    REDIS_URL: str = "redis://redis:6379/0"
    REDIS_CACHE_TTL: int = 300

    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    BINANCE_API_KEY: str = ""
    BINANCE_API_SECRET: str = ""
    BINANCE_TESTNET: bool = False

    GROK_API_KEY: str = ""
    GROK_MODEL: str = "grok-2-1212"
    LLM_TEMPERATURE: float = 0.3
    LLM_MAX_TOKENS: int = 1000

    TAVILY_API_KEY: Optional[str] = None

    MIN_POSITION_SIZE: float = 0.00000001
    MAX_POSITION_SIZE_PERCENT: float = 0.02
    DEFAULT_POSITION_SIZE_PERCENT: float = 0.01

    MAX_DAILY_LOSS_PERCENT: float = 0.05
    MAX_DRAWDOWN_PERCENT: float = 0.10

    LOG_LEVEL: str = "INFO"

    RESEND_API_KEY: Optional[str] = None
    ALERT_EMAIL_RECEIVER: str = "wambstephane@gmail.com"
    ALERT_EMAIL_SENDER: str = "onboarding@resend.dev"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
