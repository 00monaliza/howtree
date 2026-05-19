"""
Celery worker entry point.

Run with:
    celery -A worker.celery_app worker --loglevel=info --concurrency=1 -Q analysis

Key design:
- DeepForest model loaded ONCE on worker init (not per task) via `worker_process_init`.
- concurrency=1 ensures one job at a time per worker process (CPU-bound safety).
- Horizontal scaling: run multiple worker containers.
"""
from __future__ import annotations

import os

from celery import Celery
from celery.signals import worker_process_init

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger

configure_logging()
logger = get_logger("worker")
settings = get_settings()

# ── Celery app ─────────────────────────────────────────────────────────────────
celery_app = Celery(
    "tree_detection",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,          # Retry on worker crash
    worker_prefetch_multiplier=1, # Don't grab next task until current finishes
    task_routes={"app.modules.jobs.celery_tasks.run_analysis_task": {"queue": "analysis"}},
    worker_max_tasks_per_child=settings.celery_max_tasks_per_child,
    task_soft_time_limit=settings.celery_task_timeout,
    task_time_limit=settings.celery_task_timeout + 300,
    broker_connection_retry_on_startup=True,
)

# Register the task explicitly (avoids autodiscovery issues with large ML imports)
from app.modules.jobs.celery_tasks import run_analysis_task  # noqa: E402

celery_app.task(
    run_analysis_task,
    name="app.modules.jobs.celery_tasks.run_analysis_task",
    base=None,
    bind=False,
    acks_late=True,
    max_retries=0,  # No auto-retry — analysis is expensive and idempotent issues
)


@worker_process_init.connect
def warm_up_model(**kwargs):
    """
    Load DeepForest model weights into memory when the worker process starts.
    This runs once per worker process, not once per task.
    """
    logger.info("worker_warming_up_model")
    try:
        from app.modules.detection.detector import load_model
        load_model()
        logger.info("worker_model_ready")
    except Exception as exc:
        logger.error("worker_model_warmup_failed", error=str(exc))
        # Don't crash the worker — let it handle per-task failure gracefully


if __name__ == "__main__":
    celery_app.start()
