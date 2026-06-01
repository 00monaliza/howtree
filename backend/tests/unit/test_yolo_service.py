"""Unit tests for YoloService — tile download and model inference are mocked."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.detection.yolo_detector import RawDetection, YoloDetector
from app.modules.gis.coordinate_transform import TileSpec
from app.services.yolo_service import CountResult, YoloService


def _tile(center_lon: float = 71.45, center_lat: float = 51.15) -> TileSpec:
    return TileSpec(
        center_lon=center_lon,
        center_lat=center_lat,
        zoom=18,
        width_px=400,
        height_px=400,
        lon_min=center_lon - 0.005,
        lat_min=center_lat - 0.005,
        lon_max=center_lon + 0.005,
        lat_max=center_lat + 0.005,
    )


def _detector(raw: list[RawDetection]) -> YoloDetector:
    m = MagicMock(spec=YoloDetector)
    m.predict.return_value = raw
    return m


SMALL_BBOX = [71.4, 51.1, 71.41, 51.11]   # ~0.7 km² — under 5 km² limit
LARGE_BBOX = [71.0, 51.0, 71.8, 51.6]    # ~66 km² — over limit


@pytest.mark.asyncio
async def test_count_trees_zero_detections():
    svc = YoloService(_detector([]))
    tile = _tile()

    with (
        patch("app.services.yolo_service.bbox_to_tiles", return_value=[tile]),
        patch("app.services.yolo_service.TileDownloader") as DL,
        patch("app.services.yolo_service.get_map_provider", return_value=MagicMock()),
    ):
        DL.return_value.download_tiles = AsyncMock(
            return_value=[(tile, Path("/tmp/t.png"))]
        )
        result = await svc.count_trees(SMALL_BBOX, zoom=18, confidence=0.25)

    assert isinstance(result, CountResult)
    assert result.tree_count == 0
    assert result.detections == []
    assert result.area_km2 > 0
    assert result.inference_time_ms >= 0
    assert len(result.image_resolution) == 2


@pytest.mark.asyncio
async def test_count_trees_one_detection():
    raw = RawDetection(x1=10.0, y1=20.0, x2=50.0, y2=60.0, confidence=0.9)
    svc = YoloService(_detector([raw]))
    tile = _tile()

    with (
        patch("app.services.yolo_service.bbox_to_tiles", return_value=[tile]),
        patch("app.services.yolo_service.TileDownloader") as DL,
        patch("app.services.yolo_service.get_map_provider", return_value=MagicMock()),
    ):
        DL.return_value.download_tiles = AsyncMock(
            return_value=[(tile, Path("/tmp/t.png"))]
        )
        result = await svc.count_trees(SMALL_BBOX, zoom=18, confidence=0.25)

    assert result.tree_count == 1
    assert len(result.detections) == 1
    d = result.detections[0]
    assert d.bbox_pixels == [10.0, 20.0, 50.0, 60.0]
    assert len(d.bbox_geo) == 4
    assert d.confidence == 0.9


@pytest.mark.asyncio
async def test_count_trees_area_too_large():
    svc = YoloService(_detector([]))
    with pytest.raises(ValueError, match="exceeds limit"):
        await svc.count_trees(LARGE_BBOX, zoom=18, confidence=0.25)


@pytest.mark.asyncio
async def test_image_resolution_reflects_tile_grid():
    svc = YoloService(_detector([]))
    # 4 tiles: 2 cols × 2 rows (distinct center_lon and center_lat values)
    tiles = [_tile(71.41, 51.11), _tile(71.42, 51.11), _tile(71.41, 51.12), _tile(71.42, 51.12)]

    with (
        patch("app.services.yolo_service.bbox_to_tiles", return_value=tiles),
        patch("app.services.yolo_service.TileDownloader") as DL,
        patch("app.services.yolo_service.get_map_provider", return_value=MagicMock()),
    ):
        DL.return_value.download_tiles = AsyncMock(
            return_value=[(t, Path(f"/tmp/{i}.png")) for i, t in enumerate(tiles)]
        )
        result = await svc.count_trees(SMALL_BBOX, zoom=18, confidence=0.25)

    # 2 tiles × 400px with 10% overlap (settings default): 400 + 1*int(400*0.9) = 760 per axis
    assert result.image_resolution == [760, 760]
