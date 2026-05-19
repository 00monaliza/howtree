"""
Tree service — spatial queries against the trees table.
All queries use PostGIS ST_Within / ST_MakeEnvelope for spatial filtering.
"""
from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from typing import Any

from geoalchemy2.functions import (
    ST_AsGeoJSON,
    ST_MakeEnvelope,
    ST_Within,
)
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.tree import Tree

logger = get_logger(__name__)


class TreeService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def iter_trees_geojson(
        self,
        bbox: list[float],
        min_confidence: float = 0.0,
        analysis_id: str | None = None,
        batch_size: int = 1000,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Stream trees within bbox as GeoJSON feature dicts.
        Uses server-side cursor to avoid loading all features into memory.
        """
        lon1, lat1, lon2, lat2 = bbox

        stmt = (
            select(
                Tree.id,
                ST_AsGeoJSON(Tree.location).label("geom_json"),
                Tree.confidence,
                Tree.canopy_area_m2,
                Tree.analysis_id,
            )
            .where(
                ST_Within(
                    Tree.location,
                    ST_MakeEnvelope(lon1, lat1, lon2, lat2, 4326),
                )
            )
            .where(Tree.confidence >= min_confidence)
        )

        if analysis_id:
            stmt = stmt.where(Tree.analysis_id == uuid.UUID(analysis_id))

        stmt = stmt.order_by(Tree.confidence.desc())

        result = await self._session.stream(stmt)
        async for row in result:
            import json
            geom = json.loads(row.geom_json)
            yield {
                "type": "Feature",
                "geometry": geom,
                "properties": {
                    "id": str(row.id),
                    "confidence": round(row.confidence, 4),
                    "canopy_area_m2": (
                        round(row.canopy_area_m2, 2) if row.canopy_area_m2 else None
                    ),
                    "analysis_id": str(row.analysis_id),
                },
            }

    async def count_in_bbox(self, bbox: list[float]) -> int:
        lon1, lat1, lon2, lat2 = bbox
        result = await self._session.execute(
            select(func.count(Tree.id)).where(
                ST_Within(
                    Tree.location,
                    ST_MakeEnvelope(lon1, lat1, lon2, lat2, 4326),
                )
            )
        )
        return result.scalar_one()
