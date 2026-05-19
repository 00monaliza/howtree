"""
GET /jobs/{job_id} — poll job status.
WS /ws/jobs/{job_id} — stream live progress.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.logging import get_logger
from app.core.websocket_manager import ws_manager
from app.schemas.jobs import JobStatusResponse
from app.services.job_service import JobService

logger = get_logger(__name__)
router = APIRouter()


@router.get(
    "/{job_id}",
    response_model=JobStatusResponse,
    summary="Get analysis job status",
)
async def get_job_status(
    job_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
) -> JobStatusResponse:
    svc = JobService(session)
    job = await svc.get_job(job_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    return JobStatusResponse(
        job_id=str(job.id),
        status=job.status,  # type: ignore[arg-type]
        progress=job.progress,
        stage=job.stage,
        tree_count=job.tree_count,
        canopy_area_m2=job.canopy_area_m2,
        avg_confidence=job.avg_confidence,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error_message=job.error_message,
    )


@router.websocket("/ws/{job_id}")
async def job_progress_websocket(
    job_id: uuid.UUID,
    websocket: WebSocket,
) -> None:
    await ws_manager.connect(str(job_id), websocket)
    try:
        await ws_manager.stream_job_progress(str(job_id), websocket)
    except WebSocketDisconnect:
        logger.info("ws_client_disconnected", job_id=str(job_id))
    finally:
        ws_manager.disconnect(str(job_id), websocket)
