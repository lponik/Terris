"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv


EXPECTED_CATEGORIES = ("landfill", "military_base", "industrial_frs", "superfund_npl")


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
    port: int = 8000
    cache_size: int = 5000
    version: str = "0.1.0"
    cache_rounding_decimals: int = 4
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
    report_cache_ttl_seconds: int = 259200
    report_cache_max_items: int = 2000



def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be an integer, got {raw!r}") from exc


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
    port = _get_int("PORT", 8000)
    cache_size = _get_int("CACHE_SIZE", 5000)
    cache_rounding_decimals = _get_int("CACHE_ROUNDING_DECIMALS", 4)
    environment = _get_environment()
    report_cache_ttl_seconds = _get_int("REPORT_CACHE_TTL_SECONDS", 259200)
    report_cache_max_items = _get_int("REPORT_CACHE_MAX_ITEMS", 2000)

    if port <= 0:
        raise ValueError(f"PORT must be > 0, got {port}")
    if cache_size <= 0:
        raise ValueError(f"CACHE_SIZE must be > 0, got {cache_size}")
    if cache_rounding_decimals < 0 or cache_rounding_decimals > 8:
        raise ValueError(
            f"CACHE_ROUNDING_DECIMALS must be between 0 and 8, got {cache_rounding_decimals}"
        )
    if report_cache_ttl_seconds <= 0:
        raise ValueError(f"REPORT_CACHE_TTL_SECONDS must be > 0, got {report_cache_ttl_seconds}")
    if report_cache_max_items <= 0:
        raise ValueError(f"REPORT_CACHE_MAX_ITEMS must be > 0, got {report_cache_max_items}")

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
        port=port,
        cache_size=cache_size,
        version=os.getenv("APP_VERSION", "0.1.0"),
        cache_rounding_decimals=cache_rounding_decimals,
        environment=environment,
        frontend_origin=frontend_origin,
        cors_allow_origins=cors_allow_origins,
        report_cache_ttl_seconds=report_cache_ttl_seconds,
        report_cache_max_items=report_cache_max_items,
    )
