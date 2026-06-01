"""
Trees router:
  GET  /geojson — return trees within bbox as GeoJSON FeatureCollection.
  POST /count   — run YOLOv8 inference on satellite tiles and count trees.
"""
from __future__ import annotations

import json
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.logging import get_logger
from app.core.security import validate_bbox
from app.schemas.trees_count import CountRequest, CountResponse, DetectionOut
from app.services.tree_service import TreeService
from app.services.yolo_service import YoloService

logger = get_logger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Dependency: resolve YoloService from app.state
# ---------------------------------------------------------------------------

def get_yolo_service(request: Request) -> YoloService:
    model = getattr(request.app.state, "yolo_model", None)
    if model is None:
        raise HTTPException(
            status_code=503,
            detail="Tree detection model is not available",
        )
    return YoloService(model)


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


# ---------------------------------------------------------------------------
# POST /count
# ---------------------------------------------------------------------------

@router.post("/count", response_model=CountResponse, summary="Count trees in bbox using YOLOv8")
async def count_trees(
    body: CountRequest,
    svc: YoloService = Depends(get_yolo_service),
) -> CountResponse:
    """
    Run YOLOv8 inference on satellite tiles covering the given bbox and return
    the number of detected trees along with per-detection metadata.

    Errors:
      422 — invalid bbox / area too large (ValueError from YoloService or Pydantic)
      503 — model not loaded or tile download failure (RuntimeError / missing model)
      500 — unexpected internal error
    """
    try:
        result = await svc.count_trees(
            bbox=body.bbox,
            zoom=body.zoom,
            confidence=body.confidence,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return CountResponse(
        tree_count=result.tree_count,
        detections=[
            DetectionOut(
                bbox_pixels=d.bbox_pixels,
                bbox_geo=d.bbox_geo,
                confidence=d.confidence,
            )
            for d in result.detections
        ],
        area_km2=result.area_km2,
        inference_time_ms=result.inference_time_ms,
        image_resolution=result.image_resolution,
    )
