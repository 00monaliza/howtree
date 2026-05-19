from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class AnalyzeRequest(BaseModel):
    bbox: list[float] = Field(
        ...,
        min_length=4,
        max_length=4,
        description="[lon1, lat1, lon2, lat2] in WGS-84",
        examples=[[71.40, 51.10, 71.50, 51.20]],
    )
    zoom: int = Field(default=18, ge=14, le=20)

    @field_validator("bbox")
    @classmethod
    def validate_bbox_values(cls, v: list[float]) -> list[float]:
        lon1, lat1, lon2, lat2 = v
        if not (-180 <= lon1 < lon2 <= 180):
            raise ValueError(f"Longitudes must satisfy -180 ≤ lon1 < lon2 ≤ 180, got {lon1}, {lon2}")
        if not (-90 <= lat1 < lat2 <= 90):
            raise ValueError(f"Latitudes must satisfy -90 ≤ lat1 < lat2 ≤ 90, got {lat1}, {lat2}")
        return v


class AnalyzeResponse(BaseModel):
    job_id: str
    status: str = "queued"
    message: str = "Analysis job created. Connect to WebSocket for live progress."
