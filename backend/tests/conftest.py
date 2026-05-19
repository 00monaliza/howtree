"""
Pytest configuration and fixtures.
"""
import os

import pytest

# Use test settings before importing anything from app
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("APP_DEBUG", "true")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test_tree")
os.environ.setdefault("SYNC_DATABASE_URL", "postgresql+psycopg2://test:test@localhost:5432/test_tree")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/15")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/15")
os.environ.setdefault("YANDEX_MAPS_API_KEY", "test_key")
os.environ.setdefault("MAPBOX_TOKEN", "test_token")
os.environ.setdefault("MAP_PROVIDER", "yandex")


@pytest.fixture
def sample_bbox():
    return [71.40, 51.10, 71.50, 51.20]


@pytest.fixture
def small_bbox():
    return [71.40, 51.10, 71.42, 51.11]
