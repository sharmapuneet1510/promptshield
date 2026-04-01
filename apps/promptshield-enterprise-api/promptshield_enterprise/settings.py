"""
Enterprise API application settings.

All settings can be overridden via environment variables or a .env file.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Pydantic Settings for the PromptShield Enterprise API.

    All fields can be set via environment variables (case-insensitive).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://promptshield:changeme@localhost:5432/promptshield",
        description="Async PostgreSQL connection URL.",
    )

    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL.",
    )

    # Security
    SECRET_KEY: str = Field(
        default="change-me-to-a-secure-random-key-at-least-32-chars",
        description="Secret key for signing/verification.",
    )
    API_KEY_HEADER: str = Field(
        default="X-API-Key",
        description="HTTP header name used for API key authentication.",
    )
    PROMPTSHIELD_API_KEY: str = Field(
        default="ps-dev-key-change-me",
        description="Master API key for accessing the Enterprise API.",
    )
    PROMPTSHIELD_ADMIN_KEY: str = Field(
        default="ps-admin-key-change-me",
        description="Admin API key for privileged operations.",
    )

    # CORS
    ALLOWED_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        description="List of allowed CORS origins.",
    )

    # App
    ENVIRONMENT: str = Field(
        default="development",
        description="Runtime environment: development | staging | production.",
    )
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Log level: DEBUG | INFO | WARNING | ERROR.",
    )
    MAX_WORKERS: int = Field(
        default=4,
        gt=0,
        description="Number of worker processes.",
    )

    # Privacy
    STORE_RAW_PROMPTS: bool = Field(
        default=False,
        description="Whether to store raw prompt text in the database.",
    )

    # Config
    CONFIG_DIR: Path | None = Field(
        default=None,
        description="Path to custom config directory. If None, uses bundled defaults.",
    )

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v: Any) -> list[str]:
        """Accept comma-separated string or list."""
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @field_validator("LOG_LEVEL")
    @classmethod
    def uppercase_log_level(cls, v: str) -> str:
        return v.upper()

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower() == "development"


# Module-level singleton
_settings: Settings | None = None


def get_settings() -> Settings:
    """Return the cached application settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
