from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


JobStatus = Literal[
    "queued",
    "downloading_tiles",
    "running_detection",
    "merging_results",
    "storing_results",
    "completed",
    "failed",
]


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: int
    stage: Optional[str] = None
    tree_count: Optional[int] = None
    canopy_area_m2: Optional[float] = None
    avg_confidence: Optional[float] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class JobSummary(BaseModel):
    job_id: str
    status: JobStatus
    tree_count: Optional[int] = None
    canopy_area_m2: Optional[float] = None
    avg_confidence: Optional[float] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    bbox: Optional[list[float]] = None  # [lon1, lat1, lon2, lat2]


class JobListResponse(BaseModel):
    jobs: list[JobSummary]
    total: int
