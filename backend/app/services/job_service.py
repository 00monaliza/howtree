"""
JobService — creates and retrieves analysis jobs.
Decoupled from Celery dispatch to keep routes thin.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from geoalchemy2.shape import from_shape
from shapely.geometry import box
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.analysis_job import AnalysisJob

logger = get_logger(__name__)
settings = get_settings()


class JobService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_job(self, bbox: list[float], zoom: int = 18) -> AnalysisJob:
        lon1, lat1, lon2, lat2 = bbox
        bbox_geom = from_shape(box(lon1, lat1, lon2, lat2), srid=4326)

        job = AnalysisJob(
            bbox=bbox_geom,
            zoom=zoom,
            map_provider=settings.map_provider,
            status="queued",
        )
        self._session.add(job)
        await self._session.commit()
        await self._session.refresh(job)

        # Dispatch Celery task after DB commit
        self._dispatch_task(job.id, bbox, zoom)

        return job

    def _dispatch_task(
        self, job_id: uuid.UUID, bbox: list[float], zoom: int
    ) -> None:
        from app.modules.jobs.celery_tasks import run_analysis_task

        run_analysis_task.apply_async(
            args=[str(job_id), bbox, zoom],
            queue="analysis",
            task_id=str(job_id),
        )
        logger.info("celery_task_dispatched", job_id=str(job_id))

    async def get_job(self, job_id: uuid.UUID) -> AnalysisJob | None:
        result = await self._session.execute(
            select(AnalysisJob).where(AnalysisJob.id == job_id)
        )
        return result.scalar_one_or_none()
