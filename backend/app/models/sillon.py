"""Entidad Sillon."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.audit import AuditMixin


class Sillon(Base, AuditMixin):
    __tablename__ = "sillon"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    consultorio_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("consultorio.id"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(80), nullable=False)

    __table_args__ = (Index("ix_sillon_consultorio", "consultorio_id"),)
