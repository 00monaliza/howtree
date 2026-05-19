"""
Statistical calculations for tree density and canopy coverage.
"""
from __future__ import annotations

import math


def compute_bbox_area_km2(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """
    Compute bounding box area in km² using the haversine-based approximation.
    Accurate to <0.5% for areas under 100 km².
    """
    R = 6_371.0  # km
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    lon1_r, lon2_r = math.radians(lon1), math.radians(lon2)

    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r

    # Height and width of bbox in km
    height_km = R * dlat
    width_km = R * math.cos((lat1_r + lat2_r) / 2) * dlon

    return abs(height_km * width_km)


def compute_density(tree_count: int, area_km2: float) -> float:
    if area_km2 <= 0:
        return 0.0
    return round(tree_count / area_km2, 1)


def compute_canopy_coverage_pct(canopy_area_m2: float, bbox_area_km2: float) -> float:
    bbox_area_m2 = bbox_area_km2 * 1_000_000
    if bbox_area_m2 <= 0:
        return 0.0
    return round(min(100.0, (canopy_area_m2 / bbox_area_m2) * 100), 2)


def confidence_distribution(confidences: list[float]) -> dict[str, int]:
    """Bin confidence scores into named tiers."""
    dist = {"high": 0, "medium_high": 0, "medium": 0, "low": 0}
    for c in confidences:
        if c >= 0.9:
            dist["high"] += 1
        elif c >= 0.7:
            dist["medium_high"] += 1
        elif c >= 0.5:
            dist["medium"] += 1
        else:
            dist["low"] += 1
    return dist
