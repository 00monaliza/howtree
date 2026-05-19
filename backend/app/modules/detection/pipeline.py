"""
Full tree detection pipeline.

Orchestrates:
1. Tile grid generation
2. Tile download
3. DeepForest inference per tile
4. Pixel → geographic coordinate conversion
5. NMS deduplication
6. Canopy area estimation
7. Return final Detection list
"""
from __future__ import annotations

import asyncio
import math
import tempfile
from collections.abc import Callable
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import get_logger
from app.modules.detection.deduplication import Detection, nms
from app.modules.detection.detector import predict_tile
from app.modules.detection.tiler import TileDownloader, get_map_provider
from app.modules.gis.coordinate_transform import TileSpec, bbox_to_tiles, pixel_to_geo

logger = get_logger(__name__)
settings = get_settings()

ProgressCallback = Callable[[int, str], None]

# Earth radius for canopy area estimation
_EARTH_R = 6_378_137.0


def _estimate_canopy_area_m2(det: Detection) -> float:
    """
    Approximate canopy footprint area in m² from geographic bbox.
    Uses spherical approximation — good enough for sub-100m polygons.
    """
    lat_m = 111_111
    lon_m = 111_111 * math.cos(math.radians(det.lat))
    width = (det.lon_max - det.lon_min) * lon_m
    height = (det.lat_max - det.lat_min) * lat_m
    return width * height


def _infer_tile(tile: TileSpec, image_path: Path) -> list[Detection]:
    """Run inference on one tile and convert results to geographic Detections."""
    import pandas as pd

    df = predict_tile(image_path)
    if df.empty:
        return []

    detections: list[Detection] = []
    for _, row in df.iterrows():
        # Centre pixel of bounding box
        cx = (row["xmin"] + row["xmax"]) / 2
        cy = (row["ymin"] + row["ymax"]) / 2

        centre_lon, centre_lat = pixel_to_geo(cx, cy, tile)
        lon_min, lat_max = pixel_to_geo(row["xmin"], row["ymin"], tile)
        lon_max, lat_min = pixel_to_geo(row["xmax"], row["ymax"], tile)

        det = Detection(
            lon=centre_lon,
            lat=centre_lat,
            lon_min=min(lon_min, lon_max),
            lat_min=min(lat_min, lat_max),
            lon_max=max(lon_min, lon_max),
            lat_max=max(lat_min, lat_max),
            confidence=float(row["score"]),
        )
        det = Detection(
            lon=det.lon,
            lat=det.lat,
            lon_min=det.lon_min,
            lat_min=det.lat_min,
            lon_max=det.lon_max,
            lat_max=det.lat_max,
            confidence=det.confidence,
            canopy_area_m2=_estimate_canopy_area_m2(det),
        )
        detections.append(det)

    return detections


async def run_detection_pipeline(
    bbox: list[float],
    zoom: int = 18,
    progress_cb: ProgressCallback | None = None,
) -> list[Detection]:
    """
    Full async detection pipeline.

    Args:
        bbox: [lon1, lat1, lon2, lat2]
        zoom: tile zoom level
        progress_cb: optional (progress_pct, message) callback

    Returns:
        Deduplicated list of Detection objects.
    """
    lon1, lat1, lon2, lat2 = bbox

    def emit(pct: int, msg: str):
        if progress_cb:
            progress_cb(pct, msg)
        logger.info("pipeline_progress", pct=pct, msg=msg)

    # ── 1. Generate tile grid ─────────────────────────────────────
    emit(5, "Generating tile grid")
    tiles = bbox_to_tiles(
        lon1, lat1, lon2, lat2,
        zoom=zoom,
        tile_size_px=settings.tile_size,
        overlap=settings.tile_overlap,
    )
    logger.info("tile_grid_generated", count=len(tiles))

    # ── 2. Download tiles ─────────────────────────────────────────
    emit(10, f"Downloading {len(tiles)} satellite tiles")
    provider = get_map_provider()
    downloader = TileDownloader(provider=provider)

    with tempfile.TemporaryDirectory(prefix="tree_tiles_") as tmpdir:
        work_dir = Path(tmpdir)
        tile_paths = await downloader.download_tiles(tiles, work_dir)

        emit(35, "Tiles downloaded. Running DeepForest inference")

        # ── 3. Inference (CPU-bound, run in executor) ─────────────
        loop = asyncio.get_event_loop()
        all_detections: list[Detection] = []

        for idx, (tile, path) in enumerate(tile_paths):
            pct = 35 + int((idx / len(tile_paths)) * 45)
            msg = f"Running inference on tile {idx + 1}/{len(tile_paths)}"
            emit(pct, msg)

            dets = await loop.run_in_executor(None, _infer_tile, tile, path)
            all_detections.extend(dets)

        logger.info("raw_detections", count=len(all_detections))

    # ── 4. NMS deduplication ──────────────────────────────────────
    emit(82, f"Deduplicating {len(all_detections)} raw detections")
    final = nms(all_detections, iou_threshold=0.3)

    emit(90, f"Detection complete: {len(final)} trees found")
    logger.info("final_detections", count=len(final))

    return final
