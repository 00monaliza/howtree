"""
SQLAlchemy model for detected trees.
Each row = one tree detection result with spatial location.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class Tree(Base):
    __tablename__ = "trees"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Point(lon, lat) in WGS-84
    location: Mapped[object] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326), nullable=False
    )

    # Detection bounding box (pixel-derived, converted to geo)
    bbox: Mapped[Optional[object]] = mapped_column(
        Geometry(geometry_type="POLYGON", srid=4326), nullable=True
    )

    # ML confidence score [0, 1]
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # Estimated canopy footprint area in m²
    canopy_area_m2: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Foreign key to the analysis job that created this detection
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        # Spatial index for bbox queries
        Index("ix_trees_location_gist", "location", postgresql_using="gist"),
        Index("ix_trees_bbox_gist", "bbox", postgresql_using="gist"),
        # Covering index for common query pattern: analysis + confidence filter
        Index("ix_trees_analysis_confidence", "analysis_id", "confidence"),
    )

    def __repr__(self) -> str:
        return f"<Tree {self.id} confidence={self.confidence:.2f}>"
