from __future__ import annotations

import asyncio
import base64
import io
import math
import tempfile
import threading
import uuid
from pathlib import Path
from typing import Any, Literal

import cv2
import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PIL import Image, ImageDraw

from app.modules.detection.deduplication import Detection, nms
from app.modules.detection.image_pipeline import process_uploaded_image
from app.modules.detection.pipeline import _infer_tile
from app.modules.detection.tiler import EsriProvider, MapboxProvider, YandexProvider, TileDownloader
from app.modules.gis.coordinate_transform import bbox_to_tiles, pixel_to_geo
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title="HowTree Direct Detection API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)


class DetectionResponse(BaseModel):
    tree_count: int
    green_coverage_pct: float
    avg_canopy_area_m2: float
    result_boxes_base64: str
    result_centers_base64: str


class BBoxRequest(BaseModel):
    lon_min: float
    lat_min: float
    lon_max: float
    lat_max: float
    tile_source: Literal["esri", "mapbox", "osm", "yandex"] = "esri"

def _provider_for_source(tile_source: str):
    if tile_source == "yandex":
        return YandexProvider(settings.yandex_maps_api_key or "")
    if tile_source == "mapbox" and settings.mapbox_token:
        return MapboxProvider(settings.mapbox_token)
    return EsriProvider()


def _img_to_b64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode()


def _build_response(
    detections: list[Detection],
    lon_min: float,
    lat_min: float,
    lon_max: float,
    lat_max: float,
) -> DetectionResponse:
    tree_count = len(detections)

    lat_m = 111_111.0
    lon_m = 111_111.0 * math.cos(math.radians((lat_min + lat_max) / 2))
    bbox_area_m2 = max((lon_max - lon_min) * lon_m * (lat_max - lat_min) * lat_m, 1.0)

    total_canopy = sum(d.canopy_area_m2 or 0.0 for d in detections)
    green_coverage_pct = round(total_canopy / bbox_area_m2 * 100, 2)
    avg_canopy_area_m2 = round(total_canopy / tree_count, 2) if tree_count > 0 else 0.0

    W, H = 800, 800

    def geo_to_px(lon: float, lat: float) -> tuple[int, int]:
        denom_x = lon_max - lon_min or 1.0
        denom_y = lat_max - lat_min or 1.0
        x = int((lon - lon_min) / denom_x * W)
        y = int((lat_max - lat) / denom_y * H)
        return max(0, min(W - 1, x)), max(0, min(H - 1, y))

    boxes_img = Image.new("RGB", (W, H), (15, 25, 15))
    draw_b = ImageDraw.Draw(boxes_img)
    for d in detections:
        x1, y1 = geo_to_px(d.lon_min, d.lat_max)
        x2, y2 = geo_to_px(d.lon_max, d.lat_min)
        draw_b.rectangle([x1, y1, x2, y2], outline=(34, 197, 94), width=1)

    centers_img = Image.new("RGB", (W, H), (15, 25, 15))
    draw_c = ImageDraw.Draw(centers_img)
    for d in detections:
        x, y = geo_to_px(d.lon, d.lat)
        draw_c.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(34, 197, 94))

    return DetectionResponse(
        tree_count=tree_count,
        green_coverage_pct=green_coverage_pct,
        avg_canopy_area_m2=avg_canopy_area_m2,
        result_boxes_base64=_img_to_b64(boxes_img),
        result_centers_base64=_img_to_b64(centers_img),
    )


@app.post("/detect/bbox", response_model=DetectionResponse)
async def detect_bbox(req: BBoxRequest):
    provider = _provider_for_source(req.tile_source)
    tiles = bbox_to_tiles(
        req.lon_min, req.lat_min, req.lon_max, req.lat_max,
        zoom=18,
        tile_size_px=settings.tile_size,
        overlap=settings.tile_overlap,
    )
    downloader = TileDownloader(provider=provider)

    with tempfile.TemporaryDirectory(prefix="tree_api_bbox_") as tmpdir:
        work_dir = Path(tmpdir)
        tile_paths = await downloader.download_tiles(tiles, work_dir)

        loop = asyncio.get_event_loop()
        all_detections: list[Detection] = []
        for tile, path in tile_paths:
            dets = await loop.run_in_executor(None, _infer_tile, tile, path)
            all_detections.extend(dets)

    final = nms(all_detections, iou_threshold=0.3)
    return _build_response(final, req.lon_min, req.lat_min, req.lon_max, req.lat_max)


@app.post("/detect/image", response_model=DetectionResponse)
async def detect_image(file: UploadFile = File(...)):
    allowed_exts = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}
    ext = Path(file.filename or "upload.jpg").suffix.lower()
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File exceeds 50 MB limit")

    tmp_path = Path(f"/tmp/upload_{uuid.uuid4().hex}{ext}")
    try:
        tmp_path.write_bytes(content)
        detections = process_uploaded_image(tmp_path, 0.0, 0.0, 1.0, 1.0)
        return _build_response(detections, 0.0, 0.0, 1.0, 1.0)
    finally:
        tmp_path.unlink(missing_ok=True)

_WEIGHTS_PATH = Path(__file__).parent / "weights" / "model_best.pth"
_CONFIG_PATH = Path(__file__).parent.parent / "train_config.yaml"

_predictor_lock = threading.Lock()
_predictor: Any = None
_predictor_error: str | None = None


def _load_predictor() -> None:
    global _predictor, _predictor_error
    with _predictor_lock:
        if _predictor is not None or _predictor_error is not None:
            return
        try:
            from detectron2.config import get_cfg
            from detectron2.engine import DefaultPredictor

            if not _WEIGHTS_PATH.exists():
                raise FileNotFoundError(
                    f"Model weights not found at {_WEIGHTS_PATH}. "
                    "Run backend/setup.sh or manually place model_best.pth at that path."
                )
            cfg = get_cfg()
            cfg.merge_from_file(str(_CONFIG_PATH))
            cfg.MODEL.WEIGHTS = str(_WEIGHTS_PATH)
            cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.3
            cfg.MODEL.ROI_HEADS.NUM_CLASSES = 1
            cfg.MODEL.DEVICE = "cpu"
            _predictor = DefaultPredictor(cfg)
        except Exception as exc:
            _predictor_error = str(exc)


def _get_predictor() -> Any:
    if _predictor is None and _predictor_error is None:
        _load_predictor()
    if _predictor_error:
        raise RuntimeError(f"Detectron2 model unavailable: {_predictor_error}")
    return _predictor


def _masks_to_geojson_features(
    instances: Any,
    pixel_to_geo_fn,  # callable(px, py) -> [lon, lat]
) -> list[dict]:
    features = []
    for i in range(len(instances)):
        score = float(instances.scores[i])
        mask = instances.pred_masks[i].numpy().astype(np.uint8) * 255
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            if len(cnt) < 3:
                continue
            pts = cnt.squeeze(1)
            if pts.ndim != 2:
                continue
            geo_ring = [pixel_to_geo_fn(float(pt[0]), float(pt[1])) for pt in pts]
            geo_ring.append(geo_ring[0])  # close polygon ring
            features.append({
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": [geo_ring]},
                "properties": {"confidence": score, "label": "tree"},
            })
    return features


@app.post("/predict")
async def predict_from_image(
    file: UploadFile = File(...),
    lon_min: float = Form(0.0),
    lat_min: float = Form(0.0),
    lon_max: float = Form(1.0),
    lat_max: float = Form(1.0),
):
    """Run Detectron2 Mask R-CNN on an uploaded image, return tree polygon GeoJSON."""
    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File exceeds 50 MB limit")

    nparr = np.frombuffer(content, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Cannot decode image")

    try:
        predictor = _get_predictor()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    loop = asyncio.get_event_loop()
    outputs = await loop.run_in_executor(None, predictor, img)
    instances = outputs["instances"].to("cpu")

    h, w = img.shape[:2]
    # Uploaded image: use simple WGS84 linear mapping (user-supplied bbox)
    def _px_to_geo(px: float, py: float) -> list[float]:
        return [
            lon_min + (px / w) * (lon_max - lon_min),
            lat_max - (py / h) * (lat_max - lat_min),
        ]

    features = _masks_to_geojson_features(instances, _px_to_geo)
    return {"type": "FeatureCollection", "features": features}


# ── /predict/bbox: download tiles → DeepForest → GeoJSON bboxes ──────────────────

@app.post("/predict/bbox")
async def predict_from_bbox(req: BBoxRequest):
    """Download satellite tiles for a bbox, run DeepForest on each, return GeoJSON polygons."""
    from app.modules.detection.pipeline import _infer_tile

    provider = _provider_for_source(req.tile_source)
    tiles = bbox_to_tiles(
        req.lon_min, req.lat_min, req.lon_max, req.lat_max,
        zoom=18,
        tile_size_px=settings.tile_size,
        overlap=settings.tile_overlap,
    )
    downloader = TileDownloader(provider=provider)

    loop = asyncio.get_event_loop()
    all_features: list[dict] = []

    with tempfile.TemporaryDirectory(prefix="tree_predict_bbox_") as tmpdir:
        work_dir = Path(tmpdir)
        tile_paths = await downloader.download_tiles(tiles, work_dir)

        from app.modules.detection.deduplication import nms as _nms
        all_dets = []
        for tile, path in tile_paths:
            dets = await loop.run_in_executor(None, _infer_tile, tile, path)
            all_dets.extend(dets)

        final = _nms(all_dets, iou_threshold=0.3)

        from app.modules.gis.coordinate_transform import pixel_to_geo as _p2g
        for det in final:
            all_features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[det.lon_min, det.lat_min], [det.lon_max, det.lat_min],
                                     [det.lon_max, det.lat_max], [det.lon_min, det.lat_max],
                                     [det.lon_min, det.lat_min]]],
                },
                "properties": {"confidence": det.confidence, "label": "tree"},
            })

    return {"type": "FeatureCollection", "features": all_features}
