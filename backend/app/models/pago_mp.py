"""Pago de Mercado Pago vinculado a un intento de seña (C-09)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import TZTimestamp
from app.models.audit import AuditMixin


class PagoMP(Base, AuditMixin):
    __tablename__ = "pago_mp"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    intento_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("intento_sena.id"), nullable=False
    )
    payment_id: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    estado_proveedor: Mapped[str] = mapped_column(String(20), nullable=False)
    monto_centavos: Mapped[int] = mapped_column(Integer, nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False, default="ARS", server_default="ARS")
    receptor_id: Mapped[str] = mapped_column(String(120), nullable=False)
    modo: Mapped[str] = mapped_column(String(20), nullable=False, default="mock", server_default="mock")
    resultado: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pendiente", server_default="pendiente"
    )
    fecha_aprobacion_proveedor: Mapped[datetime | None] = mapped_column(
        TZTimestamp(), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "estado_proveedor IN ('approved','rejected','in_process','pending','cancelled','refunded','charged_back')",
            name="ck_pago_mp_estado_proveedor",
        ),
        CheckConstraint(
            "resultado IN ('aplicado','incidencia','pendiente')",
            name="ck_pago_mp_resultado",
        ),
        CheckConstraint("modo IN ('mock','sandbox','production')", name="ck_pago_mp_modo"),
        CheckConstraint("monto_centavos > 0", name="ck_pago_mp_monto_pos"),
        Index("ix_pago_mp_intento", "intento_id"),
        Index("ix_pago_mp_payment", "payment_id"),
        Index("ix_pago_mp_resultado", "resultado"),
    )
