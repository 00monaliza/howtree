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

from celery.signals import worker_process_init

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger

configure_logging()
logger = get_logger("worker")
settings = get_settings()

# Register tasks explicitly (avoids autodiscovery issues with large ML imports)
from app.modules.jobs.celery_tasks import run_analysis_task, run_image_analysis_task  # noqa: E402

run_analysis_task = celery_app.task(
    name="app.modules.jobs.celery_tasks.run_analysis_task",
    base=None,
    bind=False,
    acks_late=True,
    max_retries=0,
)(run_analysis_task)

run_image_analysis_task = celery_app.task(
    name="app.modules.jobs.celery_tasks.run_image_analysis_task",
    base=None,
    bind=False,
    acks_late=True,
    max_retries=0,
)(run_image_analysis_task)


@worker_process_init.connect
def warm_up_model(**kwargs):
    logger.info("worker_warming_up_model")
    try:
        from app.modules.detection.detector import _ensure_loaded
        _ensure_loaded()
        logger.info("worker_model_ready")
    except Exception as exc:
        logger.error("worker_model_warmup_failed", error=str(exc))


if __name__ == "__main__":
    celery_app.start()
