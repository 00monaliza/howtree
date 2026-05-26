"""
Simple synchronous tree detection API.

Standalone FastAPI entry-point for direct, synchronous inference without
the Celery job queue — intended for lightweight / demo usage.

Run with: uvicorn backend.api:app --port 8001
"""
from __future__ import annotations

import asyncio
import base64
import io
import math
import tempfile
import uuid
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PIL import Image, ImageDraw

from app.modules.detection.deduplication import Detection, nms
from app.modules.detection.image_pipeline import process_uploaded_image
from app.modules.detection.pipeline import _infer_tile
from app.modules.detection.tiler import EsriProvider, MapboxProvider, TileDownloader
from app.modules.gis.coordinate_transform import bbox_to_tiles
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title="HowTree Direct Detection API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)


# ── Response / request models ───────────────────────────────────────────────────

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
    tile_source: Literal["esri", "mapbox", "osm"] = "esri"


# ── Helpers ─────────────────────────────────────────────────────────────────────

def _provider_for_source(tile_source: str):
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


# ── Endpoints ───────────────────────────────────────────────────────────────────

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
