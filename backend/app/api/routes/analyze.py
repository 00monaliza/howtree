"""
POST /analyze — create an analysis job and dispatch to Celery.
POST /analyze/upload — upload an image file for tree detection.
Both return immediately with job_id.
"""
from __future__ import annotations

import shutil
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.logging import get_logger
from app.core.security import validate_bbox
from app.modules.detection.tiler import get_map_provider
from app.schemas.analyze import AnalyzeRequest, AnalyzeResponse
from app.services.job_service import JobService

logger = get_logger(__name__)
router = APIRouter()

UPLOAD_DIR = Path(tempfile.gettempdir()) / "howtree_uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".tif", ".tiff", ".jpg", ".jpeg", ".png"}
MAX_UPLOAD_BYTES = 500 * 1024 * 1024  # 500 MB


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
    try:
        get_map_provider()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    svc = JobService(session)
    job = await svc.create_job(bbox=body.bbox, zoom=body.zoom)

    logger.info("analysis_job_created", job_id=str(job.id), bbox=body.bbox)

    return AnalyzeResponse(job_id=str(job.id))


@router.post(
    "/upload",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload an image for tree detection",
)
async def upload_image_analysis(
    file: UploadFile = File(...),
    lon_min: float = Form(...),
    lat_min: float = Form(...),
    lon_max: float = Form(...),
    lat_max: float = Form(...),
    session: AsyncSession = Depends(get_async_session),
) -> AnalyzeResponse:
    # Validate file type
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported file type '{suffix}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Validate bbox
    if lon_min >= lon_max or lat_min >= lat_max:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid bbox: lon_min/lat_min must be less than lon_max/lat_max",
        )

    # Save uploaded file
    file_id = uuid.uuid4().hex
    dest_path = UPLOAD_DIR / f"{file_id}{suffix}"
    try:
        with dest_path.open("wb") as out:
            shutil.copyfileobj(file.file, out)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save uploaded file",
        ) from exc

    if dest_path.stat().st_size > MAX_UPLOAD_BYTES:
        dest_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds 500 MB limit",
        )

    # Create job record with a synthetic bbox matching the user-supplied coords
    svc = JobService(session)
    job = await svc.create_image_job(
        image_path=str(dest_path),
        lon_min=lon_min,
        lat_min=lat_min,
        lon_max=lon_max,
        lat_max=lat_max,
    )

    logger.info(
        "image_upload_job_created",
        job_id=str(job.id),
        filename=file.filename,
        path=str(dest_path),
    )

    return AnalyzeResponse(job_id=str(job.id))
