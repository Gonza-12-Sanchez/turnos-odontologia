"""Cálculo de disponibilidad y cache Redis (C-05)."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import redis as redis_client
from app.models import Bloqueo, Sillon, Tratamiento, Turno
from app.schemas.turnos import HorarioLibreOut
from app.shared.agenda_time import fecha_argentina, limites_dia_argentino


def _to_date(value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return fecha_argentina(value)
    return date.fromisoformat(str(value)[:10])


class DisponibilidadService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _tratamiento(self, tratamiento_id: UUID) -> Tratamiento:
        tratamiento = await self.session.get(Tratamiento, tratamiento_id)
        if tratamiento is None:
            raise HTTPException(status_code=404, detail="Tratamiento inexistente")
        if not tratamiento.is_active:
            raise HTTPException(status_code=422, detail="Tratamiento inactivo")
        return tratamiento

    async def _sillones(self, sillon_id: UUID | None) -> list[Sillon]:
        if sillon_id is not None:
            sillon = await self.session.get(Sillon, sillon_id)
            if sillon is None:
                raise HTTPException(status_code=404, detail="Sillón inexistente")
            if not sillon.is_active:
                raise HTTPException(status_code=422, detail="Sillón inactivo")
            return [sillon]
        result = await self.session.scalars(select(Sillon).where(Sillon.is_active.is_(True)))
        return list(result.all())

    async def _turnos_activos(self, fecha: date, sillon_ids: list[UUID]) -> list[Turno]:
        start, end = limites_dia_argentino(fecha)
        result = await self.session.scalars(
            select(Turno).where(
                Turno.is_active.is_(True),
                Turno.estado.notin_(("cancelado", "ausente")),
                Turno.sillon_id.in_(sillon_ids),
                Turno.inicio < end,
                Turno.fin > start,
            )
        )
        return list(result.all())

    async def _bloqueos_activos(self, fecha: date) -> list[Bloqueo]:
        start, end = limites_dia_argentino(fecha)
        result = await self.session.scalars(
            select(Bloqueo).where(
                Bloqueo.is_active.is_(True),
                Bloqueo.desde < end,
                Bloqueo.hasta > start,
            )
        )
        return list(result.all())

    def _cache_key(self, fecha: date, tratamiento_id: UUID, sillon_id: UUID | None) -> str:
        return f"avail:ar:{fecha.isoformat()}:{tratamiento_id}:{sillon_id or 'all'}"

    async def libres(
        self,
        fecha: Any,
        tratamiento_id: UUID,
        sillon_id: UUID | None = None,
        use_cache: bool = True,
    ) -> list[HorarioLibreOut]:
        fecha_date = _to_date(fecha)
        tratamiento = await self._tratamiento(tratamiento_id)
        cache_key = self._cache_key(fecha_date, tratamiento_id, sillon_id)

        redis = redis_client.get_redis()
        if use_cache:
            try:
                cached = await redis.get(cache_key)
                if cached:
                    data = json.loads(cached)
                    return [HorarioLibreOut.model_validate(item) for item in data]
            except (ValueError, TypeError, RedisError, OSError):
                pass

        sillones = await self._sillones(sillon_id)
        sillon_ids = [s.id for s in sillones]
        turnos = await self._turnos_activos(fecha_date, sillon_ids)
        bloqueos = await self._bloqueos_activos(fecha_date)

        duration = timedelta(minutes=tratamiento.duracion_min)
        day_start, day_end = limites_dia_argentino(fecha_date)

        slots: list[HorarioLibreOut] = []
        current = day_start
        while current + duration <= day_end:
            slot_end = current + duration
            for sillon in sillones:
                occupied = any(
                    t.sillon_id == sillon.id and t.inicio < slot_end and t.fin > current
                    for t in turnos
                )
                blocked = any(
                    (b.sillon_id is None or b.sillon_id == sillon.id)
                    and b.desde < slot_end
                    and b.hasta > current
                    for b in bloqueos
                )
                if not occupied and not blocked:
                    slots.append(HorarioLibreOut(sillon_id=sillon.id, inicio=current, fin=slot_end))
            current += duration

        slots.sort(key=lambda s: (str(s.sillon_id), s.inicio))

        if use_cache:
            try:
                payload = json.dumps([s.model_dump(mode="json") for s in slots], default=str)
                await redis.set(cache_key, payload, ex=60)
            except (RedisError, OSError):
                pass

        return slots

    async def invalidar(self, fecha: date | datetime | str | None = None) -> None:
        scope = f"{_to_date(fecha).isoformat()}:*" if fecha is not None else "*"
        redis = redis_client.get_redis()
        prefix = getattr(redis, "prefix", "") or ""
        pattern = f"{prefix}avail:ar:{scope}"
        try:
            keys = [key.removeprefix(prefix) async for key in redis.scan_iter(match=pattern)]
            if keys:
                await redis.execute_command("DEL", *keys)
        except (RedisError, OSError, RuntimeError):
            pass
