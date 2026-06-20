"""
Application configuration via Pydantic Settings.
All values sourced from environment variables / .env file.
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Literal

from pydantic import AnyUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────
    app_env: Literal["development", "staging", "production"] = "development"
    app_debug: bool = False
    app_secret_key: str = "change-me"
    api_prefix: str = "/api/v1"

    # ── Database ─────────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql+asyncpg://tree_app:password@localhost:5432/tree_detection"
    )
    sync_database_url: str = Field(
        default="postgresql+psycopg2://tree_app:password@localhost:5432/tree_detection"
    )
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30

    # ── Redis ────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # ── Imagery ──────────────────────────────────────────────────
    yandex_maps_api_key: str = ""
    mapbox_token: str = ""
    map_provider: Literal["yandex", "mapbox", "esri"] = "esri"

    # ── Detection ────────────────────────────────────────────────
    tile_size: int = 400
    tile_overlap: float = 0.2
    detection_confidence_threshold: float = 0.3
    max_bbox_area_km2: float = 50.0  # safety limit per job

    # ── YOLO Real-time ───────────────────────────────────────────
    yolo_model_path: str = "../deepforest_unified_astana.pt"
    yolo_confidence: float = 0.25
    yolo_max_bbox_area_km2: float = 5.0

    # ── Celery ───────────────────────────────────────────────────
    celery_concurrency: int = 1
    celery_max_tasks_per_child: int = 10
    celery_task_timeout: int = 3600  # 1 hour hard limit

    # ── CORS ─────────────────────────────────────────────────────
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("yandex_maps_api_key", "mapbox_token", mode="before")
    @classmethod
    def normalize_provider_secret(cls, v: str | None) -> str:
        if not v:
            return ""
        value = v.strip()
        lowered = value.lower()
        if lowered.startswith("your_") or lowered in {"change-me", "changeme"}:
            return ""
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
