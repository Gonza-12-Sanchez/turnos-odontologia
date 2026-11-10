"""Claves de idempotencia de solicitud (C-09)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import TZTimestamp
from app.models.audit import AuditMixin


class IdempotenciaSolicitud(Base, AuditMixin):
    __tablename__ = "idempotencia_solicitud"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("usuario.id"), nullable=True
    )
    operacion: Mapped[str] = mapped_column(String(40), nullable=False)
    clave: Mapped[str] = mapped_column(String(120), nullable=False)
    huella: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resultado: Mapped[dict[str, Any] | None] = mapped_column(
        sa.JSON(none_as_null=True), nullable=True
    )
    fecha: Mapped[datetime] = mapped_column(
        TZTimestamp(), nullable=False, server_default=sa.func.now()
    )

    __table_args__ = (
        Index(
            "ix_idempotencia_usuario_operacion_clave",
            "usuario_id",
            "operacion",
            "clave",
            unique=True,
        ),
        Index("ix_idempotencia_fecha", "fecha"),
    )
