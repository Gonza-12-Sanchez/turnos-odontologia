"""Historial persistido de acciones sobre turnos."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import TZTimestamp


class TurnoEvento(Base):
    __tablename__ = "turno_evento"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    turno_id: Mapped[UUID] = mapped_column(ForeignKey("turno.id"))
    actor_id: Mapped[UUID | None] = mapped_column(ForeignKey("usuario.id"))
    accion: Mapped[str] = mapped_column(String(40))
    origen: Mapped[str] = mapped_column(String(20))
    motivo: Mapped[str | None] = mapped_column(String(200))
    fecha: Mapped[datetime] = mapped_column(TZTimestamp(), server_default=func.now())

    __table_args__ = (Index("ix_turno_evento_turno_fecha", "turno_id", "fecha"),)
