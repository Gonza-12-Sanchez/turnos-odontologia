"""Entidad Cobro (montos en centavos INTEGER, RN-CO-03)."""

from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.audit import AuditMixin


class Cobro(Base, AuditMixin):
    __tablename__ = "cobro"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    turno_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("turno.id"), nullable=False
    )
    monto_centavos: Mapped[int] = mapped_column(Integer, nullable=False)
    medio: Mapped[str] = mapped_column(String(20), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    estado_mp: Mapped[str | None] = mapped_column(String(20), nullable=True)
    referencia_mp: Mapped[str | None] = mapped_column(String(120), nullable=True)

    __table_args__ = (
        CheckConstraint("monto_centavos >= 0", name="ck_cobro_monto_centavos"),
        CheckConstraint(
            "medio IN ('efectivo','transferencia','mercadopago')", name="ck_cobro_medio"
        ),
        CheckConstraint("tipo IN ('sena','total')", name="ck_cobro_tipo"),
        CheckConstraint(
            "estado_mp IS NULL OR estado_mp IN ('pendiente','aprobado')",
            name="ck_cobro_estado_mp",
        ),
        Index("ix_cobro_turno", "turno_id"),
    )
