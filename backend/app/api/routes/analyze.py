"""
POST /analyze — create an analysis job and dispatch to Celery.
Returns immediately with job_id.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.logging import get_logger
from app.core.security import validate_bbox
from app.schemas.analyze import AnalyzeRequest, AnalyzeResponse
from app.services.job_service import JobService

logger = get_logger(__name__)
router = APIRouter()


@router.post(
    "",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a tree detection analysis job",
)
async def submit_analysis(
    body: AnalyzeRequest,
    session: AsyncSession = Depends(get_async_session),
) -> AnalyzeResponse:
    try:
        validate_bbox(body.bbox)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    svc = JobService(session)
    job = await svc.create_job(bbox=body.bbox, zoom=body.zoom)

    logger.info("analysis_job_created", job_id=str(job.id), bbox=body.bbox)

    return AnalyzeResponse(job_id=str(job.id))
