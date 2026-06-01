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
    inference_time_ms: float
    image_resolution: list[int]  # [width_px, height_px]


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
        tile_w = tiles[0].width_px if tiles else settings.tile_size
        tile_h = tiles[0].height_px if tiles else settings.tile_size
        image_resolution = [
            len(unique_lons) * tile_w,
            len(unique_lats) * tile_h,
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
        elapsed_ms = (time.perf_counter() - t0) * 1000

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
