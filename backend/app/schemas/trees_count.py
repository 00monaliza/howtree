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
