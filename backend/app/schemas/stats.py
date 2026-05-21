from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DistrictStatsResponse(BaseModel):
    district: str
    city: str
    tree_count: int
    density_per_km2: float
    canopy_area_m2: float
    canopy_coverage_pct: float
    avg_confidence: float
    last_analysis: Optional[datetime] = None


class BBoxStatsResponse(BaseModel):
    tree_count: int
    area_km2: float
    density_per_km2: float
    canopy_area_m2: float
    canopy_coverage_pct: float
    avg_confidence: float
    confidence_distribution: dict[str, int]
