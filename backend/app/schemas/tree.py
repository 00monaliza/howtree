from __future__ import annotations

from pydantic import BaseModel


class TreeProperties(BaseModel):
    id: str
    confidence: float
    canopy_area_m2: float | None
    analysis_id: str


class TreeGeometry(BaseModel):
    type: str = "Point"
    coordinates: list[float]  # [lon, lat]


class TreeFeature(BaseModel):
    type: str = "Feature"
    geometry: TreeGeometry
    properties: TreeProperties


class TreeGeoJSONResponse(BaseModel):
    type: str = "FeatureCollection"
    features: list[TreeFeature]
    total_count: int
