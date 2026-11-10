"""Auditoria de cobros y senas (C-09)."""

from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import TZTimestamp
from app.models.audit import AuditMixin


class AuditoriaCobro(Base, AuditMixin):
    __tablename__ = "auditoria_cobro"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("usuario.id"), nullable=True
    )
    accion: Mapped[str] = mapped_column(String(40), nullable=False)
    cobro_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("cobro.id"), nullable=True
    )
    intento_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("intento_sena.id"), nullable=True
    )
    centavos: Mapped[int] = mapped_column(Integer, nullable=False)
    motivo: Mapped[str | None] = mapped_column(String(300), nullable=True)
    fecha: Mapped[datetime] = mapped_column(
        TZTimestamp(), nullable=False, server_default=sa.func.now()
    )

    __table_args__ = (
        CheckConstraint("centavos >= 0", name="ck_auditoria_cobro_centavos"),
        Index("ix_auditoria_cobro_cobro", "cobro_id"),
        Index("ix_auditoria_cobro_intento", "intento_id"),
        Index("ix_auditoria_cobro_fecha", "fecha"),
    )
