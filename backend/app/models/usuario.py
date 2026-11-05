"""Entidad Usuario."""

from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, Index, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.audit import AuditMixin


class Usuario(Base, AuditMixin):
    __tablename__ = "usuario"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(32), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    rol: Mapped[str] = mapped_column(String(20), nullable=False)

    __table_args__ = (
        CheckConstraint("rol IN ('paciente','odontologo','secretaria')", name="ck_usuario_rol"),
        CheckConstraint(
            "email IS NOT NULL OR telefono IS NOT NULL",
            name="ck_usuario_contacto",
        ),
        Index("uq_usuario_email", "email", unique=True),
        Index("ix_usuario_rol_activo", "rol", "is_active"),
    )
