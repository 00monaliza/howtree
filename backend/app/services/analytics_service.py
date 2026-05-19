"""
Analytics service — aggregate statistics from PostGIS.
"""
from __future__ import annotations

from geoalchemy2.functions import (
    ST_Area,
    ST_Intersects,
    ST_MakeEnvelope,
    ST_Transform,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.district import District
from app.models.tree import Tree
from app.modules.analytics.statistics import (
    compute_bbox_area_km2,
    compute_canopy_coverage_pct,
    compute_density,
    confidence_distribution,
)
from app.schemas.stats import BBoxStatsResponse, DistrictStatsResponse

logger = get_logger(__name__)


class AnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def compute_bbox_stats(self, bbox: list[float]) -> BBoxStatsResponse:
        lon1, lat1, lon2, lat2 = bbox
        envelope = ST_MakeEnvelope(lon1, lat1, lon2, lat2, 4326)

        # Aggregate query — single round-trip
        row = await self._session.execute(
            select(
                func.count(Tree.id).label("count"),
                func.avg(Tree.confidence).label("avg_conf"),
                func.sum(Tree.canopy_area_m2).label("total_canopy"),
                func.array_agg(Tree.confidence).label("confidences"),
            ).where(
                ST_Intersects(Tree.location, envelope)
            )
        )
        result = row.one()

        area_km2 = compute_bbox_area_km2(lon1, lat1, lon2, lat2)
        tree_count = result.count or 0
        total_canopy = float(result.total_canopy or 0)
        avg_conf = float(result.avg_conf or 0)
        confs = result.confidences or []

        return BBoxStatsResponse(
            tree_count=tree_count,
            area_km2=round(area_km2, 4),
            density_per_km2=compute_density(tree_count, area_km2),
            canopy_area_m2=round(total_canopy, 1),
            canopy_coverage_pct=compute_canopy_coverage_pct(total_canopy, area_km2),
            avg_confidence=round(avg_conf, 4),
            confidence_distribution=confidence_distribution(confs),
        )

    async def get_district_stats(self, district_name: str) -> DistrictStatsResponse | None:
        # Look up district boundary
        dist_row = await self._session.execute(
            select(District).where(
                func.lower(District.name) == district_name.lower()
            )
        )
        district = dist_row.scalar_one_or_none()
        if district is None:
            return None

        # Count trees inside district geometry
        row = await self._session.execute(
            select(
                func.count(Tree.id).label("count"),
                func.avg(Tree.confidence).label("avg_conf"),
                func.sum(Tree.canopy_area_m2).label("total_canopy"),
            ).where(
                ST_Intersects(Tree.location, district.geometry)
            )
        )
        result = row.one()

        # District area via PostGIS (accurate)
        area_row = await self._session.execute(
            select(
                # ST_Area on geography gives m²
                func.ST_Area(
                    func.ST_Transform(District.geometry, 32642)
                ).label("area_m2")
            ).where(District.id == district.id)
        )
        area_result = area_row.one()
        area_m2 = float(area_result.area_m2 or 1)
        area_km2 = area_m2 / 1_000_000

        tree_count = result.count or 0
        total_canopy = float(result.total_canopy or 0)
        avg_conf = float(result.avg_conf or 0)

        return DistrictStatsResponse(
            district=district.name,
            city=district.city,
            tree_count=tree_count,
            density_per_km2=compute_density(tree_count, area_km2),
            canopy_area_m2=round(total_canopy, 1),
            canopy_coverage_pct=compute_canopy_coverage_pct(total_canopy, area_km2),
            avg_confidence=round(avg_conf, 4),
        )
