"""Application configuration loaded from environment variables."""

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Application settings populated from environment variables."""

    secret_key: str = field(default_factory=lambda: os.environ.get("SECRET_KEY", "change-me-in-production"))
    csrf_secret: str = field(default_factory=lambda: os.environ.get("CSRF_SECRET", "csrf-change-me-in-production"))
    database_url: str = field(default_factory=lambda: os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///app.db"))
    debug: bool = field(default_factory=lambda: os.environ.get("DEBUG", "false").lower() == "true")
    base_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent)


settings = Settings()
