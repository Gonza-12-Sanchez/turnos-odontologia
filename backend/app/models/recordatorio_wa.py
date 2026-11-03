"""Entidad RecordatorioWA (persistencia; envío en C-08)."""

from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.audit import AuditMixin


class RecordatorioWA(Base, AuditMixin):
    __tablename__ = "recordatorio_wa"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    turno_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("turno.id"), nullable=False
    )
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    plantilla: Mapped[str] = mapped_column(String(120), nullable=False)
    message_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default="enviado", server_default="enviado"
    )
    respuesta: Mapped[str | None] = mapped_column(String(20), nullable=True)

    __table_args__ = (
        CheckConstraint("tipo IN ('recordatorio','confirmacion')", name="ck_recordatorio_tipo"),
        CheckConstraint(
            "estado IN ('enviado','entregado','leido','respondido','fallido')",
            name="ck_recordatorio_estado",
        ),
        CheckConstraint(
            "respuesta IS NULL OR respuesta IN ('confirmo','cancelo')",
            name="ck_recordatorio_respuesta",
        ),
        Index("ix_recordatorio_turno", "turno_id"),
    )
