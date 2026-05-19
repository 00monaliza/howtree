from __future__ import annotations

from datetime import datetime
from typing import Literal

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
    stage: str | None = None
    tree_count: int | None = None
    canopy_area_m2: float | None = None
    avg_confidence: float | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
