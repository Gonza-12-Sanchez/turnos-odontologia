"""Eventos de configuración: historial durable, sin baja lógica de eventos."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import TZTimestamp


class ConfigAudit(Base):
    __tablename__ = "config_audit"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="RESTRICT"),
        nullable=False,
    )
    recurso: Mapped[str] = mapped_column(String(20), nullable=False)
    recurso_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    accion: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TZTimestamp(), server_default=func.now(), nullable=False
    )
    antes: Mapped[dict | None] = mapped_column(JSONB(none_as_null=True), nullable=True)
    despues: Mapped[dict | None] = mapped_column(JSONB(none_as_null=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "recurso IN ('sillon','tratamiento','bloqueo')", name="ck_config_audit_recurso"
        ),
        CheckConstraint(
            "accion IN ('crear','actualizar','desactivar','reactivar')",
            name="ck_config_audit_accion",
        ),
        Index("ix_config_audit_recurso_fecha", "recurso", "recurso_id", "created_at"),
        Index("ix_config_audit_actor_fecha", "actor_id", "created_at"),
    )
