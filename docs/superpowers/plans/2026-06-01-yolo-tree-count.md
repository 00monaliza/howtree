# YOLOv8 Real-Time Tree Count Endpoint — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `POST /api/v1/trees/count` — a synchronous endpoint that fetches satellite tiles for a bbox, runs YOLOv8 inference, and returns tree count + geo-tagged detections in real time.

**Architecture:** New `YoloDetector` singleton (thread-safe, loads once) + `YoloService` (pipeline orchestration) + new route handler in the existing trees router. The existing DeepForest/Celery pipeline is **not touched**. YoloDetector is loaded in `app/main.py` lifespan → stored in `app.state.yolo_model`. All tile download and geo-transform utilities are reused as-is from existing modules.

**Tech Stack:** `ultralytics` (YOLOv8), `numpy`, FastAPI, Pydantic v2. Reuses: `TileDownloader`, `bbox_to_tiles`, `pixel_to_geo`, `nms`, `Detection` from `app/modules/`.

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `app/modules/detection/yolo_detector.py` | YOLOv8 model singleton: load once, thread-safe predict |
| Create | `app/services/yolo_service.py` | Pipeline: validate → tile → download → infer → NMS → result |
| Create | `app/schemas/trees_count.py` | `CountRequest` and `CountResponse` Pydantic models |
| Create | `tests/unit/test_yolo_detector.py` | Unit tests for YoloDetector (mocked YOLO) |
| Create | `tests/unit/test_yolo_service.py` | Unit tests for YoloService (mocked tile download + detector) |
| Create | `tests/unit/test_trees_count_schema.py` | Unit tests for schema validation |
| Create | `tests/unit/test_trees_count_route.py` | Unit tests for route handler |
| Create | `tests/smoke/__init__.py` | Package marker |
| Create | `tests/smoke/test_trees_count.py` | Integration smoke test against live server |
| Modify | `app/core/config.py` | Add `yolo_model_path`, `yolo_confidence`, `yolo_max_bbox_area_km2` |
| Modify | `app/core/security.py` | Expose `bbox_area_km2` as public alias |
| Modify | `app/main.py` | Load YOLO model in lifespan → `app.state.yolo_model` |
| Modify | `app/api/routes/trees.py` | Add `POST /count` handler; `GET /geojson` unchanged |
| Modify | `requirements.txt` | Add `ultralytics`, `mercantile` |
| Modify | `.env.example` | Document YOLO env vars |

All paths are relative to `backend/`.

---

## Task 1: Config fields

**Files:**
- Modify: `app/core/config.py`
- Modify: `.env.example`

- [ ] **Step 1: Add three fields to Settings in `app/core/config.py`**

After the existing `# ── Detection ─────` block (after line 56), insert:

```python
    # ── YOLO Real-time ───────────────────────────────────────────
    yolo_model_path: str = "../deepforest_urban_trees_FULL.pt"
    yolo_confidence: float = 0.25
    yolo_max_bbox_area_km2: float = 5.0
```

- [ ] **Step 2: Add vars to `.env.example`**

After the `# --- Detection ---` block, append:

```
# --- YOLO real-time endpoint ---
YOLO_MODEL_PATH=../deepforest_urban_trees_FULL.pt
YOLO_CONFIDENCE=0.25
YOLO_MAX_BBOX_AREA_KM2=5.0
```

- [ ] **Step 3: Verify settings load**

```bash
cd backend && python -c "from app.core.config import get_settings; s = get_settings(); print(s.yolo_model_path, s.yolo_confidence, s.yolo_max_bbox_area_km2)"
```

Expected: `../deepforest_urban_trees_FULL.pt 0.25 5.0`

- [ ] **Step 4: Commit**

```bash
git add app/core/config.py .env.example
git commit -m "feat(config): add YOLO real-time inference config fields"
```

---

## Task 2: Expose bbox_area_km2 as public helper

**Files:**
- Modify: `app/core/security.py`

`_bbox_area_km2` is currently private. `YoloService` needs it to validate area against `yolo_max_bbox_area_km2` (not the 50 km² Celery limit from `validate_bbox`).

- [ ] **Step 1: Add public alias at end of `app/core/security.py`**

```python
# Public alias — used by YoloService for per-request area validation
bbox_area_km2 = _bbox_area_km2
```

- [ ] **Step 2: Verify**

```bash
cd backend && python -c "from app.core.security import bbox_area_km2; print(round(bbox_area_km2(71.4, 51.1, 71.5, 51.2), 1), 'km2')"
```

Expected: a float around `60.0 km2` (the large test bbox).

- [ ] **Step 3: Commit**

```bash
git add app/core/security.py
git commit -m "feat(security): expose bbox_area_km2 as public utility function"
```

---

## Task 3: Pydantic schemas

**Files:**
- Create: `app/schemas/trees_count.py`
- Create: `tests/unit/test_trees_count_schema.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_trees_count_schema.py`:

```python
"""Unit tests for CountRequest and CountResponse schemas."""
import pytest
from app.schemas.trees_count import CountRequest, CountResponse, DetectionOut


def test_valid_bbox():
    req = CountRequest(bbox=[71.4, 51.1, 71.5, 51.2])
    assert req.bbox == [71.4, 51.1, 71.5, 51.2]
    assert req.zoom == 18
    assert req.confidence == 0.25


def test_custom_zoom_and_confidence():
    req = CountRequest(bbox=[71.4, 51.1, 71.5, 51.2], zoom=16, confidence=0.5)
    assert req.zoom == 16
    assert req.confidence == 0.5


def test_geojson_polygon_converted_to_bbox():
    geojson = {
        "type": "Polygon",
        "coordinates": [
            [[71.4, 51.1], [71.5, 51.1], [71.5, 51.2], [71.4, 51.2], [71.4, 51.1]]
        ],
    }
    req = CountRequest(geojson=geojson)
    assert req.bbox == [71.4, 51.1, 71.5, 51.2]


def test_neither_bbox_nor_geojson_raises():
    with pytest.raises(ValueError, match="bbox.*geojson"):
        CountRequest()


def test_bbox_wrong_length_raises():
    with pytest.raises(ValueError):
        CountRequest(bbox=[71.4, 51.1, 71.5])


def test_invalid_longitude_raises():
    with pytest.raises(ValueError, match="longitude"):
        CountRequest(bbox=[200.0, 51.1, 71.5, 51.2])


def test_invalid_latitude_raises():
    with pytest.raises(ValueError, match="latitude"):
        CountRequest(bbox=[71.4, -100.0, 71.5, 51.2])


def test_min_gte_max_lon_raises():
    with pytest.raises(ValueError):
        CountRequest(bbox=[71.5, 51.1, 71.4, 51.2])


def test_valid_count_response():
    resp = CountResponse(
        tree_count=5,
        detections=[
            DetectionOut(
                bbox_pixels=[0.0, 0.0, 10.0, 10.0],
                bbox_geo=[71.4, 51.1, 71.5, 51.2],
                confidence=0.9,
            )
        ],
        area_km2=0.5,
        inference_time_ms=120,
        image_resolution=[400, 400],
    )
    assert resp.tree_count == 5
    assert len(resp.detections) == 1
```

- [ ] **Step 2: Run — confirm ImportError**

```bash
cd backend && python -m pytest tests/unit/test_trees_count_schema.py -v 2>&1 | head -10
```

Expected: `ModuleNotFoundError: No module named 'app.schemas.trees_count'`

- [ ] **Step 3: Create `app/schemas/trees_count.py`**

```python
"""Pydantic schemas for POST /api/v1/trees/count."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field, model_validator


class CountRequest(BaseModel):
    bbox: Optional[list[float]] = None
    geojson: Optional[dict[str, Any]] = None
    zoom: int = Field(default=18, ge=1, le=22)
    confidence: float = Field(default=0.25, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def resolve_input(self) -> "CountRequest":
        if self.bbox is None and self.geojson is None:
            raise ValueError("Provide either 'bbox' or 'geojson'")
        if self.geojson is not None and self.bbox is None:
            try:
                coords = self.geojson["coordinates"][0]
                lons = [c[0] for c in coords]
                lats = [c[1] for c in coords]
                self.bbox = [min(lons), min(lats), max(lons), max(lats)]
            except (KeyError, IndexError, TypeError) as exc:
                raise ValueError(f"Invalid GeoJSON Polygon: {exc}") from exc
        if self.bbox is not None:
            if len(self.bbox) != 4:
                raise ValueError(
                    "bbox must have exactly 4 values: [lon_min, lat_min, lon_max, lat_max]"
                )
            lon1, lat1, lon2, lat2 = self.bbox
            if not (-180 <= lon1 < lon2 <= 180):
                raise ValueError(f"Invalid longitude range: {lon1} → {lon2}")
            if not (-90 <= lat1 < lat2 <= 90):
                raise ValueError(f"Invalid latitude range: {lat1} → {lat2}")
        return self


class DetectionOut(BaseModel):
    bbox_pixels: list[float]   # [x1, y1, x2, y2] — tile-local pixel space
    bbox_geo: list[float]      # [lon_min, lat_min, lon_max, lat_max]
    confidence: float


class CountResponse(BaseModel):
    tree_count: int
    detections: list[DetectionOut]
    area_km2: float
    inference_time_ms: int
    image_resolution: list[int]  # [total_width_px, total_height_px] of tile grid
```

- [ ] **Step 4: Run — confirm all pass**

```bash
cd backend && python -m pytest tests/unit/test_trees_count_schema.py -v
```

Expected: 9 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/schemas/trees_count.py tests/unit/test_trees_count_schema.py
git commit -m "feat(schemas): add CountRequest/CountResponse for /trees/count"
```

---

## Task 4: YoloDetector

**Files:**
- Create: `app/modules/detection/yolo_detector.py`
- Create: `tests/unit/test_yolo_detector.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_yolo_detector.py`:

```python
"""Unit tests for YoloDetector — ultralytics is mocked throughout."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.modules.detection.yolo_detector import RawDetection, YoloDetector


@pytest.fixture
def fake_pt(tmp_path) -> Path:
    p = tmp_path / "model.pt"
    p.write_bytes(b"\x00" * 16)
    return p


def _mock_yolo_with_detections(dets: list[tuple[float, float, float, float, float]]):
    """Build a mock YOLO instance that returns given (x1,y1,x2,y2,conf) detections."""
    mock_result = MagicMock()
    boxes = []
    for x1, y1, x2, y2, conf in dets:
        b = MagicMock()
        b.xyxy = [[x1, y1, x2, y2]]
        b.conf = [conf]
        boxes.append(b)
    mock_result.boxes = boxes
    mock_instance = MagicMock()
    mock_instance.model = MagicMock()
    mock_instance.predict.return_value = [mock_result]
    return mock_instance


def test_not_loaded_initially(fake_pt):
    assert not YoloDetector(fake_pt).is_loaded


def test_predict_before_load_raises(fake_pt, tmp_path):
    d = YoloDetector(fake_pt)
    img = tmp_path / "t.png"
    img.write_bytes(b"x")
    with pytest.raises(RuntimeError, match="not loaded"):
        d.predict(img)


def test_load_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        YoloDetector("/no/such/file.pt").load()


def test_load_sets_is_loaded(fake_pt):
    mock_yolo = _mock_yolo_with_detections([])
    with patch("ultralytics.YOLO", return_value=mock_yolo):
        d = YoloDetector(fake_pt)
        d.load()
    assert d.is_loaded


def test_load_is_idempotent(fake_pt):
    mock_yolo = _mock_yolo_with_detections([])
    with patch("ultralytics.YOLO", return_value=mock_yolo) as MockYOLO:
        d = YoloDetector(fake_pt)
        d.load()
        d.load()
    MockYOLO.assert_called_once()


def test_predict_returns_raw_detections(fake_pt, tmp_path):
    img = tmp_path / "tile.png"
    img.write_bytes(b"x")
    mock_yolo = _mock_yolo_with_detections([(10.0, 20.0, 50.0, 60.0, 0.85)])
    with patch("ultralytics.YOLO", return_value=mock_yolo):
        d = YoloDetector(fake_pt)
        d.load()
        results = d.predict(img, confidence=0.5)
    assert len(results) == 1
    r = results[0]
    assert isinstance(r, RawDetection)
    assert r.x1 == 10.0 and r.y1 == 20.0
    assert r.x2 == 50.0 and r.y2 == 60.0
    assert r.confidence == 0.85


def test_predict_empty_result(fake_pt, tmp_path):
    img = tmp_path / "tile.png"
    img.write_bytes(b"x")
    mock_yolo = _mock_yolo_with_detections([])
    with patch("ultralytics.YOLO", return_value=mock_yolo):
        d = YoloDetector(fake_pt)
        d.load()
        results = d.predict(img)
    assert results == []


def test_predict_inference_error_returns_empty(fake_pt, tmp_path):
    img = tmp_path / "tile.png"
    img.write_bytes(b"x")
    mock_yolo = MagicMock()
    mock_yolo.model = MagicMock()
    mock_yolo.predict.side_effect = RuntimeError("cuda error")
    with patch("ultralytics.YOLO", return_value=mock_yolo):
        d = YoloDetector(fake_pt)
        d.load()
        results = d.predict(img)
    assert results == []
```

- [ ] **Step 2: Run — confirm ImportError**

```bash
cd backend && python -m pytest tests/unit/test_yolo_detector.py -v 2>&1 | head -8
```

Expected: `ModuleNotFoundError: No module named 'app.modules.detection.yolo_detector'`

- [ ] **Step 3: Create `app/modules/detection/yolo_detector.py`**

```python
"""
YOLOv8 inference wrapper.

Singleton per process — loaded once at FastAPI startup, reused per request.
Thread-safe: double-checked locking on load(); predict() reads only.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.core.logging import get_logger

logger = get_logger(__name__)

_WARMUP_PX = 64  # blank image side for warmup forward pass


@dataclass
class RawDetection:
    """Pixel-space detection from a single tile image."""
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float


class YoloDetector:
    """Thread-safe YOLOv8 wrapper. Call load() once; predict() many times."""

    def __init__(self, model_path: str | Path) -> None:
        self._model_path = Path(model_path)
        self._model = None
        self._lock = threading.Lock()

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def load(self) -> None:
        """Load model weights and run a warmup pass. Idempotent."""
        if self._model is not None:
            return
        with self._lock:
            if self._model is not None:
                return
            if not self._model_path.exists():
                raise FileNotFoundError(f"YOLO model not found: {self._model_path}")

            logger.info("yolo_loading", path=str(self._model_path))
            t0 = time.perf_counter()

            from ultralytics import YOLO

            model = YOLO(str(self._model_path))
            model.model.eval()

            blank = np.zeros((_WARMUP_PX, _WARMUP_PX, 3), dtype=np.uint8)
            model.predict(source=blank, verbose=False, conf=0.25)

            self._model = model
            logger.info(
                "yolo_loaded",
                load_time_ms=round((time.perf_counter() - t0) * 1000),
            )

    def predict(
        self,
        image_path: Path,
        confidence: float = 0.25,
    ) -> list[RawDetection]:
        """
        Run inference on one tile PNG.

        Returns empty list on inference error (logged).
        Raises RuntimeError if model was never loaded.
        """
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load() first.")

        try:
            results = self._model.predict(
                source=str(image_path),
                conf=confidence,
                verbose=False,
            )
        except Exception as exc:
            logger.error(
                "yolo_inference_failed",
                path=str(image_path),
                error=str(exc),
            )
            return []

        detections: list[RawDetection] = []
        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0]
                detections.append(
                    RawDetection(
                        x1=float(x1),
                        y1=float(y1),
                        x2=float(x2),
                        y2=float(y2),
                        confidence=float(box.conf[0]),
                    )
                )
        return detections
```

- [ ] **Step 4: Run — confirm all pass**

```bash
cd backend && python -m pytest tests/unit/test_yolo_detector.py -v
```

Expected: 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/modules/detection/yolo_detector.py tests/unit/test_yolo_detector.py
git commit -m "feat(detection): add YoloDetector — thread-safe singleton with warmup"
```

---

## Task 5: YoloService

**Files:**
- Create: `app/services/yolo_service.py`
- Create: `tests/unit/test_yolo_service.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_yolo_service.py`:

```python
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


SMALL_BBOX = [71.4, 51.1, 71.41, 51.11]  # ~0.7 km² — under 5 km² limit
LARGE_BBOX = [71.0, 51.0, 71.8, 51.6]   # ~66 km² — over limit


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

    # 2 unique lons × 400 px, 2 unique lats × 400 px
    assert result.image_resolution == [800, 800]
```

- [ ] **Step 2: Run — confirm ImportError**

```bash
cd backend && python -m pytest tests/unit/test_yolo_service.py -v 2>&1 | head -8
```

Expected: `ModuleNotFoundError: No module named 'app.services.yolo_service'`

- [ ] **Step 3: Create `app/services/yolo_service.py`**

```python
"""
YoloService: tile fetch → YOLOv8 inference → NMS → geo-transform.

Instantiated per request; the YoloDetector model is injected.
"""
from __future__ import annotations

import asyncio
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import bbox_area_km2
from app.modules.detection.deduplication import Detection, nms
from app.modules.detection.tiler import TileDownloader, get_map_provider
from app.modules.detection.yolo_detector import RawDetection, YoloDetector
from app.modules.gis.coordinate_transform import TileSpec, bbox_to_tiles, pixel_to_geo

settings = get_settings()
logger = get_logger(__name__)


@dataclass
class DetectionResult:
    bbox_pixels: list[float]  # [x1, y1, x2, y2] — tile-local pixel space
    bbox_geo: list[float]     # [lon_min, lat_min, lon_max, lat_max]
    confidence: float


@dataclass
class CountResult:
    tree_count: int
    detections: list[DetectionResult]
    area_km2: float
    inference_time_ms: int
    image_resolution: list[int]  # [width_px, height_px] of stitched tile grid


@dataclass
class _DetectionWithPixels(Detection):
    """Carries pixel bbox through NMS alongside geo coords."""
    bbox_pixels: list[float] = field(default_factory=list)


class YoloService:
    def __init__(self, model: YoloDetector) -> None:
        self._model = model

    async def count_trees(
        self,
        bbox: list[float],
        zoom: int,
        confidence: float,
    ) -> CountResult:
        """
        Full pipeline: area check → tile grid → download → infer → NMS → return.

        Raises:
            ValueError: area > settings.yolo_max_bbox_area_km2
            RuntimeError: tile download failure
        """
        lon1, lat1, lon2, lat2 = bbox
        area = bbox_area_km2(lon1, lat1, lon2, lat2)
        if area > settings.yolo_max_bbox_area_km2:
            raise ValueError(
                f"Bounding box area {area:.2f} km² exceeds limit of "
                f"{settings.yolo_max_bbox_area_km2:.1f} km²"
            )

        t0 = time.perf_counter()

        tiles = bbox_to_tiles(
            lon1, lat1, lon2, lat2,
            zoom=zoom,
            tile_size_px=settings.tile_size,
            overlap=settings.tile_overlap,
        )

        unique_lons = {round(t.center_lon, 8) for t in tiles}
        unique_lats = {round(t.center_lat, 8) for t in tiles}
        image_resolution = [
            len(unique_lons) * settings.tile_size,
            len(unique_lats) * settings.tile_size,
        ]

        provider = get_map_provider()
        downloader = TileDownloader(provider=provider)
        loop = asyncio.get_event_loop()
        all_detections: list[Detection] = []

        with tempfile.TemporaryDirectory(prefix="yolo_tiles_") as tmpdir:
            work_dir = Path(tmpdir)
            tile_paths = await downloader.download_tiles(tiles, work_dir)

            for tile, path in tile_paths:
                tile_dets = await loop.run_in_executor(
                    None, self._infer_tile, tile, path, confidence
                )
                all_detections.extend(tile_dets)

        deduped = nms(all_detections, iou_threshold=0.3)
        elapsed_ms = round((time.perf_counter() - t0) * 1000)

        return CountResult(
            tree_count=len(deduped),
            detections=[
                DetectionResult(
                    bbox_pixels=d.bbox_pixels,  # type: ignore[attr-defined]
                    bbox_geo=[d.lon_min, d.lat_min, d.lon_max, d.lat_max],
                    confidence=d.confidence,
                )
                for d in deduped
            ],
            area_km2=round(area, 4),
            inference_time_ms=elapsed_ms,
            image_resolution=image_resolution,
        )

    def _infer_tile(
        self,
        tile: TileSpec,
        image_path: Path,
        confidence: float,
    ) -> list[_DetectionWithPixels]:
        result: list[_DetectionWithPixels] = []
        for rd in self._model.predict(image_path, confidence):
            cx = (rd.x1 + rd.x2) / 2
            cy = (rd.y1 + rd.y2) / 2
            centre_lon, centre_lat = pixel_to_geo(cx, cy, tile)
            lon_a, lat_a = pixel_to_geo(rd.x1, rd.y1, tile)
            lon_b, lat_b = pixel_to_geo(rd.x2, rd.y2, tile)
            result.append(
                _DetectionWithPixels(
                    lon=centre_lon,
                    lat=centre_lat,
                    lon_min=min(lon_a, lon_b),
                    lat_min=min(lat_a, lat_b),
                    lon_max=max(lon_a, lon_b),
                    lat_max=max(lat_a, lat_b),
                    confidence=rd.confidence,
                    bbox_pixels=[rd.x1, rd.y1, rd.x2, rd.y2],
                )
            )
        return result
```

- [ ] **Step 4: Run — confirm all pass**

```bash
cd backend && python -m pytest tests/unit/test_yolo_service.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/yolo_service.py tests/unit/test_yolo_service.py
git commit -m "feat(services): add YoloService — real-time tree count pipeline"
```

---

## Task 6: Route handler

**Files:**
- Modify: `app/api/routes/trees.py`
- Create: `tests/unit/test_trees_count_route.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_trees_count_route.py`:

```python
"""Unit tests for POST /api/v1/trees/count route handler."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.detection.yolo_detector import YoloDetector
from app.services.yolo_service import CountResult, DetectionResult


def _mock_result() -> CountResult:
    return CountResult(
        tree_count=3,
        detections=[
            DetectionResult(
                bbox_pixels=[10.0, 20.0, 50.0, 60.0],
                bbox_geo=[71.41, 51.11, 71.42, 51.12],
                confidence=0.88,
            )
        ],
        area_km2=0.05,
        inference_time_ms=120,
        image_resolution=[400, 400],
    )


@pytest.fixture
def client():
    """TestClient without lifespan — model injected directly via state."""
    app = create_app()
    mock_model = MagicMock(spec=YoloDetector)
    app.state.yolo_model = mock_model
    # No context manager → lifespan does NOT run, preventing real model load
    return TestClient(app, raise_server_exceptions=True)


@pytest.fixture
def client_no_model():
    app = create_app()
    app.state.yolo_model = None
    return TestClient(app, raise_server_exceptions=False)


def test_count_returns_200(client):
    mock_svc = MagicMock()
    mock_svc.count_trees = AsyncMock(return_value=_mock_result())
    with patch("app.api.routes.trees.YoloService", return_value=mock_svc):
        resp = client.post(
            "/api/v1/trees/count",
            json={"bbox": [71.4, 51.1, 71.41, 51.11]},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["tree_count"] == 3
    assert len(body["detections"]) == 1
    assert body["inference_time_ms"] == 120
    assert body["image_resolution"] == [400, 400]


def test_count_invalid_lon_returns_422(client):
    resp = client.post(
        "/api/v1/trees/count",
        json={"bbox": [200.0, 51.1, 71.5, 51.2]},
    )
    assert resp.status_code == 422


def test_count_no_model_returns_503(client_no_model):
    resp = client_no_model.post(
        "/api/v1/trees/count",
        json={"bbox": [71.4, 51.1, 71.41, 51.11]},
    )
    assert resp.status_code == 503


def test_count_value_error_returns_422(client):
    mock_svc = MagicMock()
    mock_svc.count_trees = AsyncMock(side_effect=ValueError("area exceeds limit"))
    with patch("app.api.routes.trees.YoloService", return_value=mock_svc):
        resp = client.post(
            "/api/v1/trees/count",
            json={"bbox": [71.4, 51.1, 71.5, 51.2]},
        )
    assert resp.status_code == 422
    assert "area exceeds limit" in resp.json()["detail"]


def test_count_runtime_error_returns_503(client):
    mock_svc = MagicMock()
    mock_svc.count_trees = AsyncMock(side_effect=RuntimeError("provider down"))
    with patch("app.api.routes.trees.YoloService", return_value=mock_svc):
        resp = client.post(
            "/api/v1/trees/count",
            json={"bbox": [71.4, 51.1, 71.41, 51.11]},
        )
    assert resp.status_code == 503


def test_geojson_input_accepted(client):
    mock_svc = MagicMock()
    mock_svc.count_trees = AsyncMock(return_value=_mock_result())
    geojson = {
        "type": "Polygon",
        "coordinates": [
            [[71.4, 51.1], [71.41, 51.1], [71.41, 51.11], [71.4, 51.11], [71.4, 51.1]]
        ],
    }
    with patch("app.api.routes.trees.YoloService", return_value=mock_svc):
        resp = client.post("/api/v1/trees/count", json={"geojson": geojson})
    assert resp.status_code == 200
```

- [ ] **Step 2: Run — confirm failures**

```bash
cd backend && python -m pytest tests/unit/test_trees_count_route.py -v 2>&1 | head -15
```

Expected: test failures (route doesn't exist yet).

- [ ] **Step 3: Replace `app/api/routes/trees.py` with full version**

```python
"""
GET  /trees/geojson  — stream tree features within bbox as GeoJSON.
POST /trees/count    — real-time YOLOv8 tree count for a bbox.
"""
from __future__ import annotations

import asyncio
import json
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.logging import get_logger
from app.core.security import validate_bbox
from app.modules.detection.yolo_detector import YoloDetector
from app.schemas.trees_count import CountRequest, CountResponse, DetectionOut
from app.services.tree_service import TreeService
from app.services.yolo_service import YoloService

logger = get_logger(__name__)
router = APIRouter()


def _get_yolo_model(request: Request) -> YoloDetector:
    model = getattr(request.app.state, "yolo_model", None)
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="YOLO model not available — check server startup logs",
        )
    return model


@router.get(
    "/geojson",
    summary="Get detected trees as GeoJSON within bbox",
    response_description="GeoJSON FeatureCollection of tree points",
)
async def get_trees_geojson(
    bbox: Annotated[
        str,
        Query(
            description="Comma-separated: lon1,lat1,lon2,lat2",
            examples=["71.40,51.10,71.50,51.20"],
        ),
    ],
    min_confidence: Annotated[float, Query(ge=0.0, le=1.0)] = 0.0,
    analysis_id: Annotated[Optional[str], Query()] = None,
    session: AsyncSession = Depends(get_async_session),
) -> StreamingResponse:
    bbox_coords = [float(x) for x in bbox.split(",")]
    validate_bbox(bbox_coords)

    svc = TreeService(session)

    async def geojson_stream():
        yield '{"type":"FeatureCollection","features":['
        first = True
        async for feature in svc.iter_trees_geojson(
            bbox=bbox_coords,
            min_confidence=min_confidence,
            analysis_id=analysis_id,
        ):
            if not first:
                yield ","
            yield json.dumps(feature)
            first = False
        yield "]}"

    return StreamingResponse(
        geojson_stream(),
        media_type="application/geo+json",
        headers={"X-Content-Type-Options": "nosniff"},
    )


@router.post(
    "/count",
    response_model=CountResponse,
    summary="Real-time tree count via YOLOv8 for a given bbox",
)
async def count_trees(
    body: CountRequest,
    model: YoloDetector = Depends(_get_yolo_model),
) -> CountResponse:
    svc = YoloService(model)
    try:
        result = await asyncio.wait_for(
            svc.count_trees(body.bbox, body.zoom, body.confidence),
            timeout=30.0,
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Inference exceeded 30s timeout",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )

    return CountResponse(
        tree_count=result.tree_count,
        detections=[
            DetectionOut(
                bbox_pixels=d.bbox_pixels,
                bbox_geo=d.bbox_geo,
                confidence=d.confidence,
            )
            for d in result.detections
        ],
        area_km2=result.area_km2,
        inference_time_ms=result.inference_time_ms,
        image_resolution=result.image_resolution,
    )
```

- [ ] **Step 4: Run — confirm all pass**

```bash
cd backend && python -m pytest tests/unit/test_trees_count_route.py -v
```

Expected: 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/api/routes/trees.py tests/unit/test_trees_count_route.py
git commit -m "feat(routes): add POST /trees/count real-time YOLO inference endpoint"
```

---

## Task 7: Model loading in lifespan

**Files:**
- Modify: `app/main.py`

- [ ] **Step 1: Add import and update lifespan in `app/main.py`**

Add at the top imports (after the existing imports):

```python
import time
from pathlib import Path

from app.modules.detection.yolo_detector import YoloDetector
```

Replace the existing `lifespan` function with:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger = get_logger(__name__)

    logger.info("startup", env=settings.app_env, provider=settings.map_provider)

    if settings.app_debug:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    model_path = Path(settings.yolo_model_path)
    yolo = YoloDetector(model_path)
    t0 = time.perf_counter()
    try:
        yolo.load()
        app.state.yolo_model = yolo
        logger.info(
            "yolo_startup_ok",
            path=str(model_path),
            load_time_ms=round((time.perf_counter() - t0) * 1000),
        )
    except Exception as exc:
        logger.error("yolo_startup_failed", error=str(exc))
        app.state.yolo_model = None

    yield

    logger.info("shutdown")
    await async_engine.dispose()
```

- [ ] **Step 2: Verify app factory loads without error**

```bash
cd backend && python -c "from app.main import create_app; app = create_app(); print('OK:', app.title)"
```

Expected: `OK: Tree Detection Platform API`

- [ ] **Step 3: Run full unit test suite to confirm nothing broke**

```bash
cd backend && python -m pytest tests/unit/ -v
```

Expected: all unit tests PASS.

- [ ] **Step 4: Commit**

```bash
git add app/main.py
git commit -m "feat(main): load YoloDetector at startup into app.state.yolo_model"
```

---

## Task 8: Update requirements.txt

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add dependencies to `requirements.txt`**

After the `# ML — DeepForest (CPU)` block, add:

```
# ML — YOLOv8 real-time inference
ultralytics>=8.0.0
mercantile>=1.2.1
```

- [ ] **Step 2: Install into venv**

```bash
cd backend && .venv/bin/pip install "ultralytics>=8.0.0" "mercantile>=1.2.1"
```

Expected: installs without error.

- [ ] **Step 3: Verify YOLO import**

```bash
cd backend && .venv/bin/python -c "import ultralytics; print('ultralytics', ultralytics.__version__)"
```

Expected: `ultralytics 8.x.x`

- [ ] **Step 4: Run all unit tests with the real package installed**

```bash
cd backend && python -m pytest tests/unit/ -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add requirements.txt
git commit -m "feat(deps): add ultralytics and mercantile for YOLO real-time inference"
```

---

## Task 9: Smoke test

**Files:**
- Create: `tests/smoke/__init__.py`
- Create: `tests/smoke/test_trees_count.py`
- Modify: `tests/conftest.py`

- [ ] **Step 1: Register `smoke` marker in conftest.py**

Add to the **bottom** of `tests/conftest.py`:

```python
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "smoke: integration tests requiring a running server on localhost:8000"
    )
```

- [ ] **Step 2: Create `tests/smoke/__init__.py`** (empty file)

- [ ] **Step 3: Create `tests/smoke/test_trees_count.py`**

```python
"""
Smoke tests for POST /api/v1/trees/count.

Requires a live server:
    cd backend && YOLO_MODEL_PATH=../deepforest_urban_trees_FULL.pt uvicorn app.main:app --port 8000

Run:
    cd backend && python -m pytest tests/smoke/ -v -m smoke
"""
from __future__ import annotations

import httpx
import pytest

BASE = "http://localhost:8000/api/v1"

# ~0.02 km² patch near Astana Botanical Garden — likely to contain trees
SAMPLE_BBOX = [71.420, 51.155, 71.435, 51.165]


@pytest.mark.smoke
def test_returns_200_with_valid_schema():
    resp = httpx.post(
        f"{BASE}/trees/count",
        json={"bbox": SAMPLE_BBOX, "zoom": 18, "confidence": 0.25},
        timeout=60.0,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "tree_count" in body
    assert body["tree_count"] >= 0
    assert isinstance(body["detections"], list)
    assert body["area_km2"] > 0
    assert body["inference_time_ms"] >= 0
    assert len(body["image_resolution"]) == 2


@pytest.mark.smoke
def test_detection_items_have_correct_fields():
    resp = httpx.post(
        f"{BASE}/trees/count",
        json={"bbox": SAMPLE_BBOX},
        timeout=60.0,
    )
    assert resp.status_code == 200
    for det in resp.json()["detections"]:
        assert len(det["bbox_pixels"]) == 4
        assert len(det["bbox_geo"]) == 4
        assert 0.0 <= det["confidence"] <= 1.0


@pytest.mark.smoke
def test_oversized_bbox_returns_422():
    resp = httpx.post(
        f"{BASE}/trees/count",
        json={"bbox": [71.0, 51.0, 71.8, 51.6]},  # ~66 km²
        timeout=10.0,
    )
    assert resp.status_code == 422
    assert "exceeds limit" in resp.json()["detail"]


@pytest.mark.smoke
def test_invalid_lon_returns_422():
    resp = httpx.post(
        f"{BASE}/trees/count",
        json={"bbox": [200.0, 51.0, 71.5, 51.5]},
        timeout=10.0,
    )
    assert resp.status_code == 422


@pytest.mark.smoke
def test_geojson_polygon_input():
    geojson = {
        "type": "Polygon",
        "coordinates": [[
            [71.420, 51.155], [71.435, 51.155],
            [71.435, 51.165], [71.420, 51.165],
            [71.420, 51.155],
        ]],
    }
    resp = httpx.post(
        f"{BASE}/trees/count",
        json={"geojson": geojson, "zoom": 18},
        timeout=60.0,
    )
    assert resp.status_code == 200
    assert resp.json()["tree_count"] >= 0
```

- [ ] **Step 4: Commit**

```bash
git add tests/smoke/ tests/conftest.py
git commit -m "test(smoke): add smoke tests for POST /trees/count"
```

- [ ] **Step 5: Start server and run smoke tests**

Terminal 1 — start server:
```bash
cd backend && YOLO_MODEL_PATH=../deepforest_urban_trees_FULL.pt uvicorn app.main:app --port 8000
```

Terminal 2 — run smoke tests:
```bash
cd backend && python -m pytest tests/smoke/ -v -m smoke
```

Expected: 5 tests PASS; `tree_count` is a non-negative integer.

---

## Self-Review

### Spec coverage

| Spec requirement | Task |
|-----------------|------|
| YoloDetector singleton, thread-safe, no reload per request | Task 4 |
| Accept image path + confidence, return detections + inference_time | Task 4 |
| Model warmup on first load | Task 4 |
| Tile fetch utility — reuse existing tiler (EsriProvider etc.) | Task 5 |
| Configurable tile URL — handled by existing `MAP_PROVIDER` config | (existing) |
| POST /api/v1/trees/count | Task 6 |
| Request: bbox or GeoJSON Polygon, zoom, confidence | Task 3 |
| Response: tree_count, detections, area_km2, inference_time_ms, image_resolution | Tasks 3, 5, 6 |
| bbox_pixels + bbox_geo per detection | Tasks 5, 6 |
| run_in_executor for non-blocking inference | Task 5 |
| 30s request timeout | Task 6 |
| bbox validation: 4 floats, ranges, min < max | Task 3 |
| 422 if area > YOLO_MAX_BBOX_AREA_KM2 | Tasks 5, 6 |
| Model loaded at startup → app.state.yolo_model | Task 7 |
| Log model load time | Task 4, 7 |
| YOLO_MODEL_PATH, YOLO_CONFIDENCE, YOLO_MAX_BBOX_AREA_KM2 config | Task 1 |
| Add ultralytics, mercantile to requirements.txt | Task 8 |
| Smoke test with sample bbox + schema check | Task 9 |
| DeepForest/Celery pipeline untouched | (all tasks — none touch those files) |

All spec requirements covered.

### Type consistency

- `RawDetection(x1, y1, x2, y2, confidence)` — defined Task 4, used in Task 5 `_infer_tile` ✓
- `_DetectionWithPixels.bbox_pixels` — defined and set in Task 5, accessed in `count_trees` ✓
- `CountResult(tree_count, detections, area_km2, inference_time_ms, image_resolution)` — defined Task 5, mapped to `CountResponse` in Task 6 ✓
- `DetectionResult(bbox_pixels, bbox_geo, confidence)` → `DetectionOut(bbox_pixels, bbox_geo, confidence)` — same field names, consistent ✓
- `YoloService(model)` instantiated in route handler, matches `__init__(self, model: YoloDetector)` ✓
- `bbox_area_km2` exported in Task 2, imported in Task 5 ✓

### Placeholder scan

No TBDs, no "add appropriate error handling", no "similar to Task N" references. All code blocks are complete.
