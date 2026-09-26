"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv


EXPECTED_CATEGORIES = ("landfill", "superfund")


def _load_env_files() -> None:
    """Load local .env files so local env vars work without manual export."""
    repo_root = Path(__file__).resolve().parents[2]
    backend_root = Path(__file__).resolve().parents[1]

    for env_path in (backend_root / ".env", repo_root / ".env"):
        if env_path.exists():
            load_dotenv(dotenv_path=env_path, override=False)


_load_env_files()


@dataclass(frozen=True)
class Settings:
    data_path: str = "data/processed/all_sites.csv"
    version: str = "0.1.0"
    environment: Literal["development", "production"] = "development"
    frontend_origin: str | None = None
    cors_allow_origins: tuple[str, ...] = (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )


def _get_environment() -> Literal["development", "production"]:
    raw = os.getenv("ENVIRONMENT", "development").strip().lower()
    if raw in {"development", "dev"}:
        return "development"
    if raw in {"production", "prod"}:
        return "production"
    raise ValueError("ENVIRONMENT must be 'development' or 'production'")


def _split_csv_values(raw: str) -> tuple[str, ...]:
    values: list[str] = []
    seen: set[str] = set()
    for item in raw.split(","):
        value = item.strip()
        if not value or value in seen:
            continue
        values.append(value)
        seen.add(value)
    return tuple(values)


def load_settings() -> Settings:
    """Create settings from environment variables."""
    environment = _get_environment()

    frontend_origin = os.getenv("FRONTEND_ORIGIN", "").strip() or None
    if environment == "production":
        if not frontend_origin:
            raise ValueError("FRONTEND_ORIGIN must be set when ENVIRONMENT=production")
        cors_allow_origins = (frontend_origin,)
    else:
        dev_origins_raw = os.getenv("DEV_CORS_ORIGINS", "").strip()
        cors_allow_origins = (
            _split_csv_values(dev_origins_raw)
            if dev_origins_raw
            else Settings.cors_allow_origins
        )
        if not cors_allow_origins:
            raise ValueError("At least one DEV_CORS_ORIGINS entry is required in development")

    return Settings(
        data_path=os.getenv("DATA_PATH", "data/processed/all_sites.csv"),
        version=os.getenv("APP_VERSION", "0.1.0"),
        environment=environment,
        frontend_origin=frontend_origin,
        cors_allow_origins=cors_allow_origins,
    )
