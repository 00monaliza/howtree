"""
GET /trees/geojson — return trees within bbox as GeoJSON FeatureCollection.
Uses streaming response for large datasets.
"""
from __future__ import annotations

import json
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.logging import get_logger
from app.core.security import validate_bbox
from app.services.tree_service import TreeService

logger = get_logger(__name__)
router = APIRouter()


@router.get(
    "/geojson",
    summary="Get detected trees as GeoJSON within bbox",
    response_description="GeoJSON FeatureCollection of tree points",
)
async def get_trees_geojson(
    bbox: Annotated[
        str,
        Query(
            description="Comma-separated: lon1,lat1,lon2,lat2",
            examples=["71.40,51.10,71.50,51.20"],
        ),
    ],
    min_confidence: Annotated[float, Query(ge=0.0, le=1.0)] = 0.0,
    analysis_id: Annotated[Optional[str], Query()] = None,
    session: AsyncSession = Depends(get_async_session),
) -> StreamingResponse:
    bbox_coords = [float(x) for x in bbox.split(",")]
    validate_bbox(bbox_coords)

    svc = TreeService(session)

    async def geojson_stream():
        """Stream GeoJSON to avoid loading all features into memory."""
        yield '{"type":"FeatureCollection","features":['
        first = True
        async for feature in svc.iter_trees_geojson(
            bbox=bbox_coords,
            min_confidence=min_confidence,
            analysis_id=analysis_id,
        ):
            if not first:
                yield ","
            yield json.dumps(feature)
            first = False
        yield "]}"

    return StreamingResponse(
        geojson_stream(),
        media_type="application/geo+json",
        headers={"X-Content-Type-Options": "nosniff"},
    )
