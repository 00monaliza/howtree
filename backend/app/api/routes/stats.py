"""
GET /stats/{district} — analytics for a named district.
GET /stats/bbox — analytics for a custom bbox.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.logging import get_logger
from app.core.security import validate_bbox
from app.schemas.stats import BBoxStatsResponse, DistrictStatsResponse
from app.services.analytics_service import AnalyticsService

logger = get_logger(__name__)
router = APIRouter()


@router.get(
    "/bbox",
    response_model=BBoxStatsResponse,
    summary="Get tree statistics for a custom bounding box",
)
async def get_bbox_stats(
    bbox: Annotated[str, Query(description="lon1,lat1,lon2,lat2")],
    session: AsyncSession = Depends(get_async_session),
) -> BBoxStatsResponse:
    coords = [float(x) for x in bbox.split(",")]
    validate_bbox(coords)

    svc = AnalyticsService(session)
    result = await svc.compute_bbox_stats(coords)
    return result


@router.get(
    "/{district}",
    response_model=DistrictStatsResponse,
    summary="Get tree statistics for a named district",
)
async def get_district_stats(
    district: str,
    session: AsyncSession = Depends(get_async_session),
) -> DistrictStatsResponse:
    svc = AnalyticsService(session)
    result = await svc.get_district_stats(district)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"District '{district}' not found",
        )

    return result
