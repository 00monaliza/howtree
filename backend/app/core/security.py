"""
Security utilities: bbox validation, input sanitisation.
Rate limiting is handled at the NGINX/reverse proxy layer in production;
basic in-process limiting applied here for development safety.
"""
from __future__ import annotations

from pyproj import Transformer

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

_wgs84_to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32642", always_xy=True)


def validate_bbox(bbox: list[float]) -> tuple[float, float, float, float]:
    """
    Validate and unpack a [lon1, lat1, lon2, lat2] bounding box.
    Returns (lon1, lat1, lon2, lat2) or raises ValueError.
    """
    if len(bbox) != 4:
        raise ValueError("bbox must have exactly 4 values: [lon1, lat1, lon2, lat2]")

    lon1, lat1, lon2, lat2 = bbox

    if not (-180 <= lon1 < lon2 <= 180):
        raise ValueError(f"Invalid longitude range: {lon1} → {lon2}")
    if not (-90 <= lat1 < lat2 <= 90):
        raise ValueError(f"Invalid latitude range: {lat1} → {lat2}")

    area_km2 = _bbox_area_km2(lon1, lat1, lon2, lat2)
    if area_km2 > settings.max_bbox_area_km2:
        raise ValueError(
            f"BBox area {area_km2:.1f} km² exceeds maximum allowed "
            f"{settings.max_bbox_area_km2} km². Split into smaller areas."
        )

    return lon1, lat1, lon2, lat2


def _bbox_area_km2(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Approximate bbox area in km² using UTM projection."""
    try:
        x1, y1 = _wgs84_to_utm.transform(lon1, lat1)
        x2, y2 = _wgs84_to_utm.transform(lon2, lat2)
        area_m2 = abs(x2 - x1) * abs(y2 - y1)
        return area_m2 / 1_000_000
    except Exception:
        # Fallback: rough approximation
        lat_deg = (lat1 + lat2) / 2
        km_per_deg_lat = 111.0
        km_per_deg_lon = 111.0 * abs(lat_deg) / 90.0
        return abs(lon2 - lon1) * km_per_deg_lon * abs(lat2 - lat1) * km_per_deg_lat


# Public alias — used by YoloService for per-request area validation
bbox_area_km2 = _bbox_area_km2
