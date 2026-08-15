"""
Application configuration via environment variables.
Uses pydantic-settings to load from .env file.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "Controle Financeiro"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = Field(
        ...,
        description="PostgreSQL connection string: postgresql+asyncpg://user:pass@host:port/db",
    )

    # JWT & Rotating Tokens
    SECRET_KEY: str = Field(..., description="Secret key for JWT signing")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # Short-lived access token (30 min)
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7     # Long-lived refresh token (7 days)

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # Excel upload
    MAX_UPLOAD_SIZE_MB: int = 5

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


settings = Settings()
