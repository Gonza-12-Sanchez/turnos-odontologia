"""Reserva de turnos con invariantes de motor (C-05)."""

from __future__ import annotations

from datetime import timedelta

from fastapi import HTTPException
from redis.exceptions import RedisError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import redis as redis_client
from app.models import Paciente, Sillon, Tratamiento, Turno
from app.schemas.turnos import HorarioLibreOut, TurnoCreate
from app.services.disponibilidad_service import DisponibilidadService


class DepositoRequerido(Exception):
    def __init__(self, checkout: dict | None = None) -> None:
        self.checkout = checkout or {"provider": "mercadopago", "status": "pendiente"}


class ReservaConflicto(Exception):
    def __init__(self, alternativas: list[HorarioLibreOut]) -> None:
        self.alternativas = alternativas


class ReservaService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.disp = DisponibilidadService(session)

    async def reservar(self, payload: TurnoCreate, paciente: Paciente, uow) -> Turno:
        sillon = await self.session.get(Sillon, payload.sillon_id)
        if sillon is None:
            raise HTTPException(status_code=404, detail="Sillón inexistente")
        if not sillon.is_active:
            raise HTTPException(status_code=422, detail="Sillón inactivo")

        tratamiento = await self.session.get(Tratamiento, payload.tratamiento_id)
        if tratamiento is None:
            raise HTTPException(status_code=404, detail="Tratamiento inexistente")
        if not tratamiento.is_active:
            raise HTTPException(status_code=422, detail="Tratamiento inactivo")

        requiere_sena = bool(payload.sena or payload.requiere_sena or payload.deposit)
        if requiere_sena:
            raise DepositoRequerido()

        inicio = payload.inicio
        fin = inicio + timedelta(minutes=tratamiento.duracion_min)
        tratamiento_id = tratamiento.id

        libres = await self.disp.libres(inicio.date(), tratamiento_id, sillon.id, use_cache=False)
        if not any(slot.inicio == inicio and slot.sillon_id == sillon.id for slot in libres):
            alts = (await self.disp.libres(inicio.date(), tratamiento_id, use_cache=False))[:3]
            raise ReservaConflicto(alts)

        turno = Turno(
            paciente_id=paciente.id,
            sillon_id=sillon.id,
            tratamiento_id=tratamiento_id,
            inicio=inicio,
            fin=fin,
            estado="reservado",
            origen="online",
            es_sobreturno=False,
        )
        self.session.add(turno)
        try:
            await self.session.flush()
            await self.session.refresh(turno)
            await uow.commit()
        except IntegrityError:
            await uow.rollback()
            alts = (await self.disp.libres(inicio.date(), tratamiento_id, use_cache=False))[:3]
            raise ReservaConflicto(alts)
        except Exception as exc:  # noqa: BLE001
            # Captura errores de concurrencia de asyncpg/SQLAlchemy que no son
            # IntegrityError (ej. InvalidRequestError, MissingGreenlet) y los
            # convierte en conflicto de reserva (409) en lugar de 500.
            await uow.rollback()
            import logging

            logging.getLogger(__name__).warning("Error inesperado al reservar: %s", exc)
            alts = (await self.disp.libres(inicio.date(), tratamiento_id, use_cache=False))[:3]
            raise ReservaConflicto(alts)

        await self.disp.invalidar(inicio.date())

        try:
            redis = redis_client.get_redis()
            await redis.lpush("wa:reminders", str(turno.id))
        except (RedisError, OSError):
            pass

        return turno

    async def alternativas(self, fecha, tratamiento_id) -> list[HorarioLibreOut]:
        libres = await self.disp.libres(fecha, tratamiento_id, use_cache=False)
        return libres[:3]
