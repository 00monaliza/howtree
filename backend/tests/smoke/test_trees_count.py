"""Smoke tests — full app lifespan runs, tile download and inference are mocked."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.modules.gis.coordinate_transform import TileSpec


SMALL_BBOX = {"bbox": [71.40, 51.10, 71.41, 51.11]}


def _fake_tile() -> TileSpec:
    return TileSpec(
        center_lon=71.405,
        center_lat=51.105,
        zoom=18,
        width_px=400,
        height_px=400,
        lon_min=71.40,
        lat_min=51.10,
        lon_max=71.41,
        lat_max=51.11,
    )


@pytest.fixture(scope="module")
def smoke_client():
    """Start the app with lifespan, but stub out the YOLO model load and tile I/O."""
    from app.main import app

    fake_tile = _fake_tile()

    with (
        patch("app.modules.detection.yolo_detector.YoloDetector") as MockDetector,
        patch("app.services.yolo_service.TileDownloader") as MockDL,
        patch("app.services.yolo_service.get_map_provider", return_value=MagicMock()),
        patch("app.services.yolo_service.bbox_to_tiles", return_value=[fake_tile]),
        # Prevent the lifespan from running `Base.metadata.create_all` (needs a real DB)
        patch("app.main.settings") as mock_settings,
    ):
        mock_settings.app_debug = False
        mock_settings.yolo_model_path = "/tmp/fake_model.pt"
        mock_settings.map_provider = "esri"
        mock_settings.api_prefix = "/api/v1"
        mock_settings.cors_origins = ["http://localhost:3000"]

        mock_det = MagicMock()
        mock_det.load.return_value = None
        mock_det.predict.return_value = []
        MockDetector.return_value = mock_det

        MockDL.return_value.download_tiles = AsyncMock(
            return_value=[(fake_tile, Path("/tmp/tile.png"))]
        )

        with TestClient(app) as client:
            yield client, mock_det


def test_smoke_count_returns_200(smoke_client):
    client, _ = smoke_client
    resp = client.post("/api/v1/trees/count", json=SMALL_BBOX)
    assert resp.status_code == 200
    body = resp.json()
    assert "tree_count" in body
    assert "detections" in body
    assert "area_km2" in body
    assert "inference_time_ms" in body
    assert "image_resolution" in body


def test_smoke_count_zero_detections(smoke_client):
    """With predict returning [], tree_count should be 0."""
    client, _ = smoke_client
    resp = client.post("/api/v1/trees/count", json=SMALL_BBOX)
    assert resp.status_code == 200
    assert resp.json()["tree_count"] == 0


def test_smoke_count_invalid_bbox_422(smoke_client):
    """Reversed bbox should be rejected with 422."""
    client, _ = smoke_client
    resp = client.post("/api/v1/trees/count", json={"bbox": [71.5, 51.1, 71.4, 51.2]})
    assert resp.status_code == 422


def test_smoke_model_ready(smoke_client):
    """Verify the lifespan actually stored a model in app.state."""
    from app.main import app
    assert app.state.yolo_model is not None
