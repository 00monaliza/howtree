"""
JobService — creates and retrieves analysis jobs.
Decoupled from Celery dispatch to keep routes thin.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from geoalchemy2.functions import ST_XMax, ST_XMin, ST_YMax, ST_YMin
from geoalchemy2.shape import from_shape
from shapely.geometry import box
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.analysis_job import AnalysisJob

logger = get_logger(__name__)
settings = get_settings()


class JobService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_job(self, bbox: list[float], zoom: int = 17) -> AnalysisJob:
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
        from app.core.celery_app import celery_app

        celery_app.send_task(
            "app.modules.jobs.celery_tasks.run_analysis_task",
            args=[str(job_id), bbox, zoom],
            queue="analysis",
            task_id=str(job_id),
        )
        logger.info("celery_task_dispatched", job_id=str(job_id))

    async def create_image_job(
        self,
        image_path: str,
        lon_min: float,
        lat_min: float,
        lon_max: float,
        lat_max: float,
    ) -> AnalysisJob:
        bbox_geom = from_shape(box(lon_min, lat_min, lon_max, lat_max), srid=4326)

        job = AnalysisJob(
            bbox=bbox_geom,
            zoom=0,
            map_provider="upload",
            status="queued",
        )
        self._session.add(job)
        await self._session.commit()
        await self._session.refresh(job)

        self._dispatch_image_task(job.id, image_path, lon_min, lat_min, lon_max, lat_max)

        return job

    def _dispatch_image_task(
        self,
        job_id: uuid.UUID,
        image_path: str,
        lon_min: float,
        lat_min: float,
        lon_max: float,
        lat_max: float,
    ) -> None:
        from app.core.celery_app import celery_app

        celery_app.send_task(
            "app.modules.jobs.celery_tasks.run_image_analysis_task",
            args=[str(job_id), image_path, lon_min, lat_min, lon_max, lat_max],
            queue="analysis",
            task_id=str(job_id),
        )
        logger.info("image_celery_task_dispatched", job_id=str(job_id))

    async def get_job(self, job_id: uuid.UUID) -> AnalysisJob | None:
        result = await self._session.execute(
            select(AnalysisJob).where(AnalysisJob.id == job_id)
        )
        return result.scalar_one_or_none()

    async def list_jobs(
        self, limit: int = 20, status_filter: str | None = None
    ) -> list[dict]:
        stmt = select(
            AnalysisJob.id,
            AnalysisJob.status,
            AnalysisJob.tree_count,
            AnalysisJob.canopy_area_m2,
            AnalysisJob.avg_confidence,
            AnalysisJob.created_at,
            AnalysisJob.completed_at,
            ST_XMin(AnalysisJob.bbox).label("lon1"),
            ST_YMin(AnalysisJob.bbox).label("lat1"),
            ST_XMax(AnalysisJob.bbox).label("lon2"),
            ST_YMax(AnalysisJob.bbox).label("lat2"),
        ).order_by(desc(AnalysisJob.created_at)).limit(limit)

        if status_filter:
            stmt = stmt.where(AnalysisJob.status == status_filter)

        rows = await self._session.execute(stmt)
        result = []
        for row in rows:
            bbox = None
            if row.lon1 is not None:
                bbox = [
                    round(float(row.lon1), 6),
                    round(float(row.lat1), 6),
                    round(float(row.lon2), 6),
                    round(float(row.lat2), 6),
                ]
            result.append({
                "job_id": str(row.id),
                "status": row.status,
                "tree_count": row.tree_count,
                "canopy_area_m2": row.canopy_area_m2,
                "avg_confidence": row.avg_confidence,
                "created_at": row.created_at,
                "completed_at": row.completed_at,
                "bbox": bbox,
            })
        return result
