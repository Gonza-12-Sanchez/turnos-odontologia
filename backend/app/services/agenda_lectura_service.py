"""Servicio de lectura de agenda y mis reservas (C-07)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.repositories.agenda_lectura_repository import AgendaLecturaRepository
from app.schemas.turnos import (
    AccionesOut,
    AgendaSillonOut,
    AgendaTurnoOut,
    MisReservaOut,
)


class AgendaLecturaService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AgendaLecturaRepository(session)

    async def agenda(
        self,
        fecha: Any,
        sillon_id: UUID | None = None,
        estado: str | None = None,
    ) -> list[AgendaSillonOut]:
        turnos = await self.repo.list_for_agenda(fecha, sillon_id, estado)
        groups: dict[Any, dict] = {}
        for turno in turnos:
            key = turno.sillon_id
            if key not in groups:
                groups[key] = {
                    "sillon_id": turno.sillon_id,
                    "sillon_nombre": turno.sillon.nombre,
                    "sillon": {"id": turno.sillon.id, "nombre": turno.sillon.nombre},
                    "turnos": [],
                }
            groups[key]["turnos"].append(self._agenda_turno(turno))
        ordered = sorted(groups.values(), key=lambda g: g["sillon_nombre"])
        return [AgendaSillonOut(**g) for g in ordered]

    def _agenda_turno(self, turno: Any) -> AgendaTurnoOut:
        return AgendaTurnoOut(
            id=turno.id,
            sillon_id=turno.sillon_id,
            sillon_nombre=turno.sillon.nombre,
            paciente_id=turno.paciente_id,
            paciente_nombre=turno.paciente.nombre,
            tratamiento_id=turno.tratamiento_id,
            tratamiento_nombre=turno.tratamiento.nombre,
            duracion_min=turno.tratamiento.duracion_min,
            inicio=turno.inicio,
            fin=turno.fin,
            estado=turno.estado,
            origen=turno.origen,
            es_sobreturno=turno.es_sobreturno,
            motivo_sobreturno=turno.motivo_sobreturno,
            tolerancia_min=settings.late_tolerance_minutes,
        )

    async def mis_reservas(
        self,
        paciente: Any,
        desde: Any = None,
        hasta: Any = None,
        estado: str | None = None,
    ) -> list[MisReservaOut]:
        paciente_id = getattr(paciente, "id", paciente)
        turnos = await self.repo.list_for_paciente(paciente_id, desde, hasta, estado)
        now = datetime.now(UTC)
        cancel_window = settings.appointment_cancel_minutes * 60
        result: list[MisReservaOut] = []
        for turno in turnos:
            cancelar = (
                turno.estado in ("reservado", "confirmado")
                and (turno.inicio - now).total_seconds() >= cancel_window
            )
            acciones = AccionesOut(
                cancelar=cancelar,
                confirmar=turno.estado == "reservado",
                reprogramar=cancelar,
            )
            result.append(
                MisReservaOut(
                    id=turno.id,
                    sillon_id=turno.sillon_id,
                    sillon_nombre=turno.sillon.nombre,
                    tratamiento_id=turno.tratamiento_id,
                    tratamiento_nombre=turno.tratamiento.nombre,
                    inicio=turno.inicio,
                    fin=turno.fin,
                    estado=turno.estado,
                    origen=turno.origen,
                    es_sobreturno=turno.es_sobreturno,
                    tolerancia_min=settings.late_tolerance_minutes,
                    acciones=acciones,
                    acciones_permitidas=acciones,
                )
            )
        return result
