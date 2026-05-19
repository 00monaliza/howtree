"""
SQLAlchemy model for administrative districts.
Pre-loaded via migration or management command.
"""
from __future__ import annotations

import uuid

from geoalchemy2 import Geometry
from sqlalchemy import Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class District(Base):
    __tablename__ = "districts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    city: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # MultiPolygon boundary in WGS-84
    geometry: Mapped[object] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=4326), nullable=False
    )

    __table_args__ = (
        Index("ix_districts_geometry_gist", "geometry", postgresql_using="gist"),
    )

    def __repr__(self) -> str:
        return f"<District {self.name}, {self.city}>"
