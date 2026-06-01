# YOLOv8 Real-Time Tree Count Endpoint — Design Spec

**Date:** 2026-06-01
**Status:** Approved
**Model:** `deepforest_urban_trees_FULL.pt` (YOLOv8, project root)

---

## Problem

The existing detection pipeline uses DeepForest and runs asynchronously via Celery jobs.
The frontend needs a **synchronous, real-time** tree count for a user-selected map bbox —
no job queue, no polling, just a single POST → response.

---

## Scope

Add one new endpoint (`POST /api/v1/trees/count`) that:
- Fetches satellite tiles for a bbox
- Runs YOLOv8 inference
- Returns tree count + detections with pixel and geo coordinates

Does **not** touch the existing DeepForest / Celery pipeline.

---

## Architecture

### New files

| File | Purpose |
|------|---------|
| `backend/app/modules/detection/yolo_detector.py` | YOLOv8 model singleton — load once, thread-safe predict |
| `backend/app/services/yolo_service.py` | `YoloService`: orchestrates tile fetch → inference → NMS → geo-transform |

### Modified files

| File | Change |
|------|--------|
| `backend/app/core/config.py` | Add `yolo_model_path`, `yolo_confidence`, `yolo_max_bbox_area_km2` (separate from existing `max_bbox_area_km2` used by Celery jobs) |
| `backend/app/main.py` | Lifespan loads YOLO model → `app.state.yolo_model`; logs load time |
| `backend/app/api/routes/trees.py` | Add `POST /count` handler; existing `GET /geojson` unchanged |
| `backend/requirements.txt` | Add `ultralytics`, `mercantile` |

### Untouched (preserved exactly)

`detector.py`, `pipeline.py`, `celery_tasks.py`, `tiler.py`, all existing Celery job logic.

---

## Data Flow

```
POST /api/v1/trees/count
       │
       ▼
1. Validate bbox (lon/lat ranges, min < max)
2. Compute area_km2 (Haversine) → reject 422 if > MAX_BBOX_AREA_KM2
       │
       ▼
3. bbox_to_tiles() → list[TileSpec]   [reuse existing gis module]
       │
       ▼
4. TileDownloader.download_tiles()    [reuse existing tiler module, async]
       │
       ▼
5. For each tile: YoloDetector.predict() via run_in_executor
   → raw detections: pixel bbox + confidence
       │
       ▼
6. pixel_to_geo() per detection bbox  [reuse existing gis module]
       │
       ▼
7. nms() deduplication                [reuse existing deduplication module]
       │
       ▼
8. Return CountResponse JSON
```

Entire handler wrapped in `asyncio.wait_for(..., timeout=30)`.

---

## API Contract

### Request

```
POST /api/v1/trees/count
Content-Type: application/json

{
  "bbox": [minLon, minLat, maxLon, maxLat],
  "zoom": 18,        // optional, default 18
  "confidence": 0.25 // optional, default from settings.yolo_confidence
}
```

GeoJSON Polygon input is also accepted: bbox is computed as `[min(lons), min(lats), max(lons), max(lats)]` from all ring coordinates.

### Response

```json
{
  "tree_count": 42,
  "detections": [
    {
      "bbox_pixels": [x1, y1, x2, y2],
      "bbox_geo": [lon_min, lat_min, lon_max, lat_max],
      "confidence": 0.87
    }
  ],
  "area_km2": 0.12,
  "inference_time_ms": 340,
  "image_resolution": [1024, 1024]
}
```

### Error responses

| Condition | HTTP | Message |
|-----------|------|---------|
| Invalid bbox coords | 422 | Descriptive validation error |
| Area > MAX_BBOX_AREA_KM2 | 422 | "Bounding box area X.Xkm² exceeds limit of Y.Ykm²" |
| Tile provider down | 503 | "Tile download failed" |
| Model not loaded | 503 | "YOLO model not available" |
| 30s timeout | 504 | "Inference timeout" |

---

## yolo_detector.py

- Singleton pattern with `threading.Lock` (same as existing `detector.py`)
- Loaded via `ultralytics.YOLO(model_path)`
- `YoloDetector.predict(image_path, confidence) → list[RawDetection]`
  - `RawDetection`: pixel bbox `[x1, y1, x2, y2]`, confidence, image size
- Model warmup: one forward pass on a blank image after load
- Thread-safe: single instance, GIL protects Python state; for true parallelism use separate processes

---

## yolo_service.py

- `YoloService(model: YoloDetector)` — injected
- `async def count_trees(bbox, zoom, confidence) → CountResult`
- Uses `asyncio.get_event_loop().run_in_executor(None, ...)` for inference
- Temp directory lifecycle: created before download, deleted after all inference completes
- Returns `CountResult` dataclass: `tree_count`, `detections`, `area_km2`, `inference_time_ms`, `image_resolution`

---

## Configuration additions (`config.py`)

| Key | Default | Description |
|-----|---------|-------------|
| `YOLO_MODEL_PATH` | `../deepforest_urban_trees_FULL.pt` | Path to .pt file, relative to backend/ dir |
| `YOLO_CONFIDENCE` | `0.25` | Default confidence threshold for real-time endpoint |
| `YOLO_MAX_BBOX_AREA_KM2` | `5.0` | Max area for /count endpoint (Celery jobs use the existing `MAX_BBOX_AREA_KM2=50.0`) |

---

## Model loading (main.py lifespan)

```python
t0 = time.perf_counter()
model = YoloDetector(settings.yolo_model_path)
model.load()
app.state.yolo_model = model
logger.info("yolo_model_loaded", load_time_ms=round((time.perf_counter() - t0) * 1000))
```

Failure to load is logged and `app.state.yolo_model = None`; the endpoint returns 503 if None.

---

## Smoke test (`backend/tests/smoke/test_trees_count.py`)

- `POST /api/v1/trees/count` with a small bbox (~0.05 km²) over a known green area
- Asserts HTTP 200, `tree_count >= 0`, response schema is valid
- 422 path: bbox area > 5 km²
- 422 path: invalid coordinates (lon > 180)
- Uses `httpx` against running server; no mocks

---

## Dependencies

Add to `requirements.txt`:
- `ultralytics` (YOLOv8)
- `mercantile` (tile math, already used conceptually)
