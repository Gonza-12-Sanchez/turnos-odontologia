"""Entidad Tratamiento."""

from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.audit import AuditMixin


class Tratamiento(Base, AuditMixin):
    __tablename__ = "tratamiento"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    duracion_min: Mapped[int] = mapped_column(Integer, nullable=False)
    precio_referencia_centavos: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        CheckConstraint("duracion_min > 0", name="ck_tratamiento_duracion_min"),
        CheckConstraint("precio_referencia_centavos >= 0", name="ck_tratamiento_precio_centavos"),
    )
