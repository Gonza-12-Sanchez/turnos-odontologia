"""Entidad Bloqueo de agenda."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import TZTimestamp
from app.models.audit import AuditMixin


class Bloqueo(Base, AuditMixin):
    __tablename__ = "bloqueo"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    sillon_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("sillon.id"), nullable=True
    )
    desde: Mapped[datetime] = mapped_column(TZTimestamp(), nullable=False)
    hasta: Mapped[datetime] = mapped_column(TZTimestamp(), nullable=False)
    motivo: Mapped[str] = mapped_column(String(120), nullable=False)

    __table_args__ = (
        CheckConstraint("hasta > desde", name="ck_bloqueo_hasta_gt_desde"),
        Index("ix_bloqueo_sillon_desde", "sillon_id", "desde"),
    )
