"""Entidad Paciente (1↔1 con Usuario rol paciente)."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.audit import AuditMixin


class Paciente(Base, AuditMixin):
    __tablename__ = "paciente"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("usuario.id"), unique=True, nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    telefono: Mapped[str] = mapped_column(String(32), nullable=False)
    obra_social: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)