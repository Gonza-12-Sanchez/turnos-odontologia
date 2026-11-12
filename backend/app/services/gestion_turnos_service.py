"""Gestión del ciclo de vida del turno (C-06)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Bloqueo, Sillon, Tratamiento, Turno, TurnoEvento
from app.repositories.paciente_repository import PacienteRepository
from app.services.disponibilidad_service import DisponibilidadService
from app.services.reserva_service import ReservaConflicto
from app.shared.agenda_time import fecha_argentina


class GestionTurnosService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.disp = DisponibilidadService(session)

    async def _turno(self, turno_id: Any) -> Turno:
        turno = await self.session.scalar(
            select(Turno).where(Turno.id == turno_id).with_for_update()
        )
        if turno is None or not turno.is_active:
            raise HTTPException(status_code=404, detail="Turno inexistente")
        return turno

    def _evento(self, turno: Turno, actor, accion: str, origin=None, motivo=None) -> None:
        origen = origin or (
            "whatsapp" if actor is None else "online" if actor.rol == "paciente" else "mostrador"
        )
        self.session.add(
            TurnoEvento(
                turno_id=turno.id,
                actor_id=actor.id if actor is not None else None,
                accion=accion,
                origen=origen,
                motivo=motivo,
            )
        )

    async def _check_owner(self, turno: Turno, actor) -> None:
        if actor.rol == "paciente":
            pac = await PacienteRepository(self.session).get_by_usuario_id(actor.id)
            if pac is None or turno.paciente_id != pac.id:
                raise HTTPException(status_code=403, detail="Acceso denegado")

    def _window_ok(self, turno: Turno) -> bool:
        now = datetime.now(UTC)
        return (turno.inicio - now).total_seconds() >= settings.appointment_cancel_minutes * 60

    async def confirmar(self, turno_id, actor=None, origin: str | None = None) -> Turno:
        if actor is not None:
            await self._check_permission(actor, ("secretaria", "paciente"))
        turno = await self._turno(turno_id)
        if actor is not None:
            await self._check_owner(turno, actor)
        if turno.estado != "reservado":
            raise HTTPException(status_code=422, detail="Transición inválida")
        turno.estado = "confirmado"
        self._evento(turno, actor, "confirmar", origin)
        effective_origin = origin or (
            "whatsapp" if actor is None else (turno.origen or "mostrador")
        )
        turno.origen = effective_origin
        await self.session.flush()
        await self.session.refresh(turno)
        return turno

    async def cancelar(self, turno_id, actor=None, origin: str | None = None) -> Turno:
        if actor is not None:
            await self._check_permission(actor, ("secretaria", "paciente"))
        turno = await self._turno(turno_id)
        if actor is not None:
            await self._check_owner(turno, actor)
        if turno.estado in ("asistido", "ausente", "cancelado"):
            raise HTTPException(status_code=422, detail="Transición inválida")
        if not self._window_ok(turno):
            raise HTTPException(status_code=422, detail="Fuera de la ventana de cancelación")
        turno.estado = "cancelado"
        self._evento(turno, actor, "cancelar", origin)
        effective_origin = origin or (
            "whatsapp" if actor is None else (turno.origen or "mostrador")
        )
        turno.origen = effective_origin
        await self.session.flush()
        await self.session.refresh(turno)
        return turno

    async def reprogramar(
        self, turno_id, inicio, sillon_id, actor, origin: str | None = None
    ) -> Turno:
        await self._check_permission(actor, ("secretaria", "paciente"))
        turno = await self._turno(turno_id)
        await self._check_owner(turno, actor)
        if turno.estado in ("asistido", "ausente", "cancelado"):
            raise HTTPException(status_code=422, detail="Transición inválida")
        if not self._window_ok(turno):
            raise HTTPException(status_code=422, detail="Fuera de la ventana de reprogramación")

        tratamiento = await self.session.get(Tratamiento, turno.tratamiento_id)
        if tratamiento is None or not tratamiento.is_active:
            raise HTTPException(status_code=422, detail="Tratamiento inactivo")

        new_sillon_id = sillon_id if sillon_id is not None else turno.sillon_id
        sillon = await self.session.get(Sillon, new_sillon_id)
        if sillon is None:
            raise HTTPException(status_code=404, detail="Sillón inexistente")
        if not sillon.is_active:
            raise HTTPException(status_code=422, detail="Sillón inactivo")

        duration = timedelta(minutes=tratamiento.duracion_min)
        new_fin = inicio + duration
        # overlap check excluding current turno
        stmt = select(Turno).where(
            Turno.is_active.is_(True),
            Turno.id != turno.id,
            Turno.estado.notin_(("cancelado", "ausente")),
            Turno.sillon_id == new_sillon_id,
            Turno.inicio < new_fin,
            Turno.fin > inicio,
        )
        conflict = (await self.session.scalars(stmt)).first()
        bloqueos_stmt = select(Bloqueo).where(
            Bloqueo.is_active.is_(True),
            Bloqueo.desde < new_fin,
            Bloqueo.hasta > inicio,
        )
        bloqueos = (await self.session.scalars(bloqueos_stmt)).all()
        blocked = any((b.sillon_id is None or b.sillon_id == new_sillon_id) for b in bloqueos)
        if conflict is not None or blocked:
            alts = (
                await self.disp.libres(
                    fecha_argentina(inicio), tratamiento.id, new_sillon_id, use_cache=False
                )
            )[:3]
            raise ReservaConflicto(alts)

        tratamiento_id = tratamiento.id
        try:
            async with self.session.begin_nested():
                turno.sillon_id = new_sillon_id
                turno.inicio = inicio
                turno.fin = new_fin
                turno.estado = "reservado"
                self._evento(turno, actor, "reprogramar", origin)
                turno.origen = origin or turno.origen or "mostrador"
                await self.session.flush()
        except IntegrityError as exc:
            if getattr(exc.orig, "sqlstate", None) != "23P01":
                raise
            alts = (
                await self.disp.libres(
                    fecha_argentina(inicio), tratamiento_id, new_sillon_id, use_cache=False
                )
            )[:3]
            raise ReservaConflicto(alts) from exc
        await self.session.refresh(turno)
        return turno

    async def marcar_asistencia(
        self, turno_id, estado: str, actor, origin: str | None = None, motivo: str | None = None
    ) -> Turno:
        await self._check_permission(actor, ("secretaria", "odontologo"))
        if estado not in ("asistido", "ausente"):
            raise HTTPException(status_code=422, detail="Estado inválido")
        turno = await self._turno(turno_id)
        if turno.estado not in ("reservado", "confirmado"):
            raise HTTPException(status_code=422, detail="Transición inválida")
        if motivo is not None and not motivo.strip():
            raise HTTPException(status_code=422, detail="Motivo requerido")
        turno.estado = estado
        self._evento(turno, actor, estado, origin, motivo.strip() if motivo else None)
        turno.origen = origin or turno.origen or "mostrador"
        await self.session.flush()
        await self.session.refresh(turno)
        return turno

    async def sobreturno(self, turno_id, motivo: str, actor, origin: str | None = None) -> Turno:
        if actor.rol != "secretaria":
            raise HTTPException(status_code=403, detail="Acceso denegado")
        if not motivo or not motivo.strip():
            raise HTTPException(status_code=422, detail="Motivo requerido")
        turno = await self._turno(turno_id)
        turno.es_sobreturno = True
        turno.motivo_sobreturno = motivo.strip()
        self._evento(turno, actor, "sobreturno", origin, motivo.strip())
        turno.origen = origin or turno.origen or "mostrador"
        await self.session.flush()
        await self.session.refresh(turno)
        return turno

    async def patch(
        self, turno_id, *, es_sobreturno=None, motivo_sobreturno=None, origen=None, actor
    ) -> Turno:
        turno = await self._turno(turno_id)
        await self._check_owner(turno, actor)
        # permission for sobreturno changes
        if (es_sobreturno is True or motivo_sobreturno is not None) and actor.rol != "secretaria":
            raise HTTPException(status_code=403, detail="Acceso denegado")
        if es_sobreturno is True:
            if not (motivo_sobreturno and motivo_sobreturno.strip()):
                raise HTTPException(status_code=422, detail="Motivo requerido")
            turno.es_sobreturno = True
            turno.motivo_sobreturno = motivo_sobreturno.strip()
            self._evento(turno, actor, "sobreturno", motivo=motivo_sobreturno.strip())
        if origen is not None and origen != turno.origen:
            turno.origen = origen
            self._evento(turno, actor, "cambiar_origen")
        await self.session.flush()
        await self.session.refresh(turno)
        return turno

    async def _check_permission(self, actor, allowed: tuple[str, ...]) -> None:
        if actor.rol not in allowed:
            raise HTTPException(status_code=403, detail="Acceso denegado")
