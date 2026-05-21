"""
Shared Celery app configuration.

The API uses this app only as a producer. The worker imports the same app and
registers executable tasks in worker.py.
"""
from __future__ import annotations

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

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
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.modules.jobs.celery_tasks.run_analysis_task": {"queue": "analysis"},
        "app.modules.jobs.celery_tasks.run_image_analysis_task": {"queue": "analysis"},
    },
    worker_max_tasks_per_child=settings.celery_max_tasks_per_child,
    task_soft_time_limit=settings.celery_task_timeout,
    task_time_limit=settings.celery_task_timeout + 300,
    broker_connection_retry_on_startup=True,
)
