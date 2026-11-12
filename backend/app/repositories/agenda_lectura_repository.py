"""Repositorio de lectura para agenda y mis reservas (C-07)."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.turno import Turno
from app.shared.agenda_time import limites_dia_argentino


def _day_start(value: date | datetime) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    return datetime.combine(value, time.min, tzinfo=UTC)


def _next_day_start(value: date | datetime) -> datetime:
    if isinstance(value, datetime):
        base = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        return base + timedelta(days=1)
    return datetime.combine(value, time.min, tzinfo=UTC) + timedelta(days=1)


class AgendaLecturaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_agenda(
        self,
        fecha: date | datetime,
        sillon_id: UUID | None = None,
        estado: str | None = None,
    ) -> list[Turno]:
        if isinstance(fecha, datetime):
            start, end = _day_start(fecha), _next_day_start(fecha)
        else:
            start, end = limites_dia_argentino(fecha)
        stmt = select(Turno).where(
            Turno.is_active.is_(True),
            Turno.inicio >= start,
            Turno.inicio < end,
        )
        if sillon_id is not None:
            stmt = stmt.where(Turno.sillon_id == sillon_id)
        if estado is not None:
            stmt = stmt.where(Turno.estado == estado)
        stmt = stmt.options(
            selectinload(Turno.paciente),
            selectinload(Turno.tratamiento),
            selectinload(Turno.sillon),
        )
        stmt = stmt.order_by(Turno.sillon_id, Turno.inicio)
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def list_for_paciente(
        self,
        paciente_id: UUID,
        desde: date | datetime | None = None,
        hasta: date | datetime | None = None,
        estado: str | None = None,
    ) -> list[Turno]:
        stmt = select(Turno).where(
            Turno.is_active.is_(True),
            Turno.paciente_id == paciente_id,
        )
        if desde is not None:
            stmt = stmt.where(Turno.inicio >= _day_start(desde))
        if hasta is not None:
            stmt = stmt.where(Turno.inicio < _next_day_start(hasta))
        if estado is not None:
            stmt = stmt.where(Turno.estado == estado)
        stmt = stmt.options(
            selectinload(Turno.paciente),
            selectinload(Turno.tratamiento),
            selectinload(Turno.sillon),
        )
        stmt = stmt.order_by(Turno.inicio)
        result = await self.session.scalars(stmt)
        return list(result.all())
