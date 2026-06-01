"""
Unit tests for POST /api/v1/trees/count endpoint.

TestClient is used WITHOUT a context manager to avoid triggering lifespan
(which would attempt to load real .pt model files).
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.yolo_service import CountResult, DetectionResult


# ---------------------------------------------------------------------------
# Shared fixture: client with a mock yolo_model in app.state
# ---------------------------------------------------------------------------

@pytest.fixture
def client(monkeypatch):
    app.state.yolo_model = MagicMock()
    yield TestClient(app)
    app.state.yolo_model = None


# ---------------------------------------------------------------------------
# Helper factory for a minimal CountResult
# ---------------------------------------------------------------------------

def _make_count_result() -> CountResult:
    return CountResult(
        tree_count=2,
        detections=[
            DetectionResult(
                bbox_pixels=[10.0, 20.0, 30.0, 40.0],
                bbox_geo=[71.40, 51.10, 71.41, 51.11],
                confidence=0.85,
            ),
            DetectionResult(
                bbox_pixels=[50.0, 60.0, 70.0, 80.0],
                bbox_geo=[71.42, 51.12, 71.43, 51.13],
                confidence=0.91,
            ),
        ],
        area_km2=0.5432,
        inference_time_ms=123.4,
        image_resolution=[512, 512],
    )


# ---------------------------------------------------------------------------
# Test 1: happy path — 200 with correct response shape
# ---------------------------------------------------------------------------

def test_count_returns_200_with_detections(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.yolo_service.YoloService.count_trees",
        AsyncMock(return_value=_make_count_result()),
    )

    resp = client.post(
        "/api/v1/trees/count",
        json={"bbox": [71.40, 51.10, 71.50, 51.20]},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["tree_count"] == 2
    assert len(data["detections"]) == 2
    assert data["area_km2"] == 0.5432
    assert data["inference_time_ms"] == 123.4
    assert data["image_resolution"] == [512, 512]
    first = data["detections"][0]
    assert first["bbox_pixels"] == [10.0, 20.0, 30.0, 40.0]
    assert first["bbox_geo"] == [71.40, 51.10, 71.41, 51.11]
    assert first["confidence"] == pytest.approx(0.85)


# ---------------------------------------------------------------------------
# Test 2: ValueError from service → 422
# ---------------------------------------------------------------------------

def test_count_value_error_returns_422(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.yolo_service.YoloService.count_trees",
        AsyncMock(side_effect=ValueError("too large")),
    )

    resp = client.post(
        "/api/v1/trees/count",
        json={"bbox": [71.40, 51.10, 71.50, 51.20]},
    )

    assert resp.status_code == 422
    assert "too large" in resp.text


# ---------------------------------------------------------------------------
# Test 3: RuntimeError from service → 503
# ---------------------------------------------------------------------------

def test_count_runtime_error_returns_503(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.yolo_service.YoloService.count_trees",
        AsyncMock(side_effect=RuntimeError("download failed")),
    )

    resp = client.post(
        "/api/v1/trees/count",
        json={"bbox": [71.40, 51.10, 71.50, 51.20]},
    )

    assert resp.status_code == 503
    assert "download failed" in resp.text


# ---------------------------------------------------------------------------
# Test 4: model not loaded → 503
# ---------------------------------------------------------------------------

def test_count_model_not_loaded_returns_503(monkeypatch):
    from app.main import app as fastapi_app
    original = fastapi_app.state.yolo_model if hasattr(fastapi_app.state, "yolo_model") else None
    fastapi_app.state.yolo_model = None
    try:
        c = TestClient(fastapi_app)
        resp = c.post(
            "/api/v1/trees/count",
            json={"bbox": [71.40, 51.10, 71.50, 51.20]},
        )
        assert resp.status_code == 503
        assert "not available" in resp.text.lower()
    finally:
        fastapi_app.state.yolo_model = original


# ---------------------------------------------------------------------------
# Test 5: invalid bbox (lon_min > lon_max) → 422 from Pydantic
# ---------------------------------------------------------------------------

def test_count_invalid_bbox_returns_422(client):
    # lon1=71.5 > lon2=71.4 → CountRequest validator rejects it
    resp = client.post(
        "/api/v1/trees/count",
        json={"bbox": [71.5, 51.1, 71.4, 51.2]},
    )

    assert resp.status_code == 422
