"""Intento de seña MP previo al turno (C-09). No retiene cupo."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import TZTimestamp
from app.models.audit import AuditMixin


class IntentoSena(Base, AuditMixin):
    __tablename__ = "intento_sena"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    paciente_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("paciente.id"), nullable=False
    )
    sillon_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("sillon.id"), nullable=False
    )
    tratamiento_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tratamiento.id"), nullable=False
    )
    inicio: Mapped[datetime] = mapped_column(TZTimestamp(), nullable=False)
    fin: Mapped[datetime] = mapped_column(TZTimestamp(), nullable=False)
    duracion_min: Mapped[int] = mapped_column(Integer, nullable=False)
    monto_centavos: Mapped[int] = mapped_column(Integer, nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False, default="ARS", server_default="ARS")
    sena_politica: Mapped[str] = mapped_column(
        String(20), nullable=False, default="deshabilitada", server_default="deshabilitada"
    )
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default="creando_checkout", server_default="creando_checkout"
    )
    preference_id: Mapped[str | None] = mapped_column(String(120), nullable=True, unique=True)
    checkout_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    turno_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("turno.id"), nullable=True, unique=True
    )
    expires_at: Mapped[datetime] = mapped_column(TZTimestamp(), nullable=False)
    modo: Mapped[str] = mapped_column(
        String(20), nullable=False, default="mock", server_default="mock"
    )

    __table_args__ = (
        CheckConstraint(
            "estado IN ('creando_checkout','pendiente','aprobado','rechazado','expirado','requiere_revision')",
            name="ck_intento_sena_estado",
        ),
        CheckConstraint("modo IN ('mock','sandbox','production')", name="ck_intento_sena_modo"),
        CheckConstraint("fin > inicio", name="ck_intento_sena_fin_gt_inicio"),
        Index("ix_intento_sena_paciente", "paciente_id"),
        Index("ix_intento_sena_estado", "estado"),
        Index("ix_intento_sena_preference", "preference_id"),
        Index("ix_intento_sena_turno", "turno_id"),
    )
