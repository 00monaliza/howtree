"""
Celery tasks for analysis jobs.

Architecture notes:
- Single Celery app, single task: `run_analysis_task`.
- All progress updates go through Redis pub/sub (websocket_manager.publish_progress).
- DB writes use the sync SQLAlchemy engine (no event loop in Celery context).
- Model loading happens in `on_worker_init` signal (see worker.py), not per-task.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from celery import Task
from geoalchemy2.shape import from_shape
from shapely.geometry import Point, box
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.websocket_manager import publish_progress
from app.models.analysis_job import AnalysisJob
from app.models.tree import Tree
from app.modules.detection.deduplication import Detection

logger = get_logger(__name__)
settings = get_settings()


def _get_celery_app():
    """Deferred import to avoid circular dependency at module load."""
    from worker import celery_app
    return celery_app


class AnalysisTask(Task):
    """Base task class with error handling and cleanup."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        job_id = args[0] if args else task_id
        logger.error("analysis_task_failed", job_id=job_id, error=str(exc))
        _mark_job_failed(job_id, str(exc))
        publish_progress(
            settings.redis_url, job_id, 0, f"Analysis failed: {exc}", status="failed"
        )

    def on_success(self, retval, task_id, args, kwargs):
        job_id = args[0] if args else task_id
        logger.info("analysis_task_success", job_id=job_id, tree_count=retval)


def _mark_job_failed(job_id: str, error: str) -> None:
    from app.core.database import get_sync_session

    session: Session = get_sync_session()
    try:
        job = session.get(AnalysisJob, uuid.UUID(job_id))
        if job:
            job.status = "failed"
            job.error_message = error[:2000]
            job.completed_at = datetime.now(timezone.utc)
            session.commit()
    except Exception as exc:
        logger.error("mark_failed_error", error=str(exc))
    finally:
        session.close()


def _update_job(
    session: Session,
    job_id: str,
    status: str,
    progress: int,
    stage: str | None = None,
    **kwargs,
) -> None:
    job = session.get(AnalysisJob, uuid.UUID(job_id))
    if not job:
        return
    job.status = status
    job.progress = progress
    if stage:
        job.stage = stage
    for k, v in kwargs.items():
        setattr(job, k, v)
    session.commit()


def run_analysis_task(job_id: str, bbox: list[float], zoom: int) -> int:
    """
    Main analysis task. Not a Celery decorator here — registered in worker.py.

    Returns:
        Number of trees detected.
    """
    from app.core.database import get_sync_session
    from app.modules.detection.pipeline import run_detection_pipeline

    logger.info("analysis_task_started", job_id=job_id, bbox=bbox)

    def emit(pct: int, msg: str, status: str = "processing"):
        publish_progress(settings.redis_url, job_id, pct, msg, status=status)
        logger.info("progress", job_id=job_id, pct=pct, msg=msg)

    session: Session = get_sync_session()
    try:
        # Mark started
        _update_job(
            session, job_id, "downloading_tiles", 5,
            stage="downloading_tiles",
            started_at=datetime.now(timezone.utc),
        )
        emit(5, "Starting analysis job")

        def progress_cb(pct: int, msg: str):
            """Bridge from async pipeline to sync Celery task."""
            _update_job(session, job_id, _status_for_pct(pct), pct, stage=_stage_for_pct(pct))
            emit(pct, msg)

        # Run async pipeline in a fresh event loop (Celery is sync)
        detections: list[Detection] = asyncio.run(
            run_detection_pipeline(bbox=bbox, zoom=zoom, progress_cb=progress_cb)
        )

        # ── Store results ──────────────────────────────────────────
        _update_job(session, job_id, "storing_results", 92, stage="storing_results")
        emit(92, f"Storing {len(detections)} trees in PostGIS")

        _store_detections(session, job_id, detections)

        # ── Finalise job ───────────────────────────────────────────
        tree_count = len(detections)
        total_canopy = sum(d.canopy_area_m2 or 0 for d in detections)
        avg_conf = (
            sum(d.confidence for d in detections) / tree_count
            if tree_count else 0.0
        )

        _update_job(
            session, job_id, "completed", 100,
            stage="completed",
            tree_count=tree_count,
            canopy_area_m2=total_canopy,
            avg_confidence=avg_conf,
            completed_at=datetime.now(timezone.utc),
        )
        emit(100, f"Analysis complete: {tree_count} trees detected", status="completed")

        logger.info("analysis_complete", job_id=job_id, trees=tree_count)
        return tree_count

    except Exception as exc:
        logger.error("analysis_error", job_id=job_id, error=str(exc), exc_info=True)
        _mark_job_failed(job_id, str(exc))
        emit(0, f"Failed: {exc}", status="failed")
        raise
    finally:
        session.close()


def _store_detections(
    session: Session, job_id: str, detections: list[Detection]
) -> None:
    """Bulk-insert tree detections, 500 at a time."""
    BATCH = 500
    job_uuid = uuid.UUID(job_id)

    for i in range(0, len(detections), BATCH):
        batch = detections[i : i + BATCH]
        tree_objects = [
            Tree(
                location=from_shape(Point(d.lon, d.lat), srid=4326),
                bbox=from_shape(
                    box(d.lon_min, d.lat_min, d.lon_max, d.lat_max), srid=4326
                ),
                confidence=d.confidence,
                canopy_area_m2=d.canopy_area_m2,
                analysis_id=job_uuid,
            )
            for d in batch
        ]
        session.bulk_save_objects(tree_objects)
        session.commit()


def _status_for_pct(pct: int) -> str:
    if pct < 35:
        return "downloading_tiles"
    if pct < 82:
        return "running_detection"
    if pct < 92:
        return "merging_results"
    if pct < 100:
        return "storing_results"
    return "completed"


def _stage_for_pct(pct: int) -> str:
    return _status_for_pct(pct)
