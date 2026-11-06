"""Entidad Turno (anti-solapamiento a nivel motor, RN-TU-01)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, String, Text, column, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import TZTimestamp

if TYPE_CHECKING:
    from app.models.paciente import Paciente
    from app.models.sillon import Sillon
    from app.models.tratamiento import Tratamiento
from app.models.audit import AuditMixin


class Turno(Base, AuditMixin):
    __tablename__ = "turno"

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
    odontologo_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("usuario.id"), nullable=True
    )
    inicio: Mapped[datetime] = mapped_column(TZTimestamp(), nullable=False)
    fin: Mapped[datetime] = mapped_column(TZTimestamp(), nullable=False)
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default="reservado", server_default="reservado"
    )
    origen: Mapped[str] = mapped_column(
        String(20), nullable=False, default="online", server_default="online"
    )
    es_sobreturno: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=sa.text("false")
    )
    motivo_sobreturno: Mapped[str | None] = mapped_column(Text, nullable=True)

    paciente: Mapped[Paciente] = relationship("Paciente")
    sillon: Mapped[Sillon] = relationship("Sillon")
    tratamiento: Mapped[Tratamiento] = relationship("Tratamiento")

    __table_args__ = (
        CheckConstraint("fin > inicio", name="ck_turno_fin_gt_inicio"),
        CheckConstraint(
            "estado IN ('reservado','confirmado','asistido','cancelado','ausente')",
            name="ck_turno_estado",
        ),
        CheckConstraint("origen IN ('online','mostrador','whatsapp')", name="ck_turno_origen"),
        ExcludeConstraint(
            ("sillon_id", "="),
            (func.tstzrange(column("inicio"), column("fin")), "&&"),
            where="is_active AND estado NOT IN ('cancelado','ausente')",
            name="ex_turno_no_solape",
            using="gist",
        ),
        Index("ix_turno_sillon_inicio", "sillon_id", "inicio"),
        Index("ix_turno_paciente_inicio", "paciente_id", "inicio"),
        Index("ix_turno_estado_inicio", "estado", "inicio"),
    )
