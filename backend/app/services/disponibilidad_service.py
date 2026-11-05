"""Cálculo de disponibilidad y cache Redis (C-05)."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from uuid import UUID

import redis.asyncio as aioredis
from fastapi import HTTPException
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import redis as redis_client
from app.models import Bloqueo, Sillon, Tratamiento, Turno
from app.schemas.turnos import HorarioLibreOut

DAY_START_HOUR = 0
DAY_END_HOUR = 24


def _to_date(value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
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
        start = datetime.combine(fecha, time.min, tzinfo=UTC)
        end = start + timedelta(days=1)
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
        start = datetime.combine(fecha, time.min, tzinfo=UTC)
        end = start + timedelta(days=1)
        result = await self.session.scalars(
            select(Bloqueo).where(
                Bloqueo.is_active.is_(True),
                Bloqueo.desde < end,
                Bloqueo.hasta > start,
            )
        )
        return list(result.all())

    def _cache_key(self, fecha: date, tratamiento_id: UUID, sillon_id: UUID | None) -> str:
        return f"avail:{fecha.isoformat()}:{tratamiento_id}:{sillon_id or 'all'}"

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
        day_start = datetime.combine(fecha_date, time.min, tzinfo=UTC)
        day_end = day_start + timedelta(days=1)

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

        try:
            payload = json.dumps([s.model_dump(mode="json") for s in slots], default=str)
            await redis.set(cache_key, payload, ex=60)
        except (RedisError, OSError):
            pass

        return slots

    async def invalidar(self, fecha: Any) -> None:
        fecha_date = _to_date(fecha)
        redis = redis_client.get_redis()
        prefix = getattr(redis, "prefix", "") or ""
        pattern = f"{prefix}avail:{fecha_date.isoformat()}:*"
        try:
            cursor: Any = 0
            keys: list[str] = []
            while True:
                cursor, batch = await aioredis.Redis.execute_command(
                    redis, "SCAN", cursor, "MATCH", pattern, "COUNT", 100
                )
                keys.extend(batch or [])
                if str(cursor) == "0":
                    break
            if keys:
                await aioredis.Redis.execute_command(redis, "DEL", *keys)
        except (RedisError, OSError, RuntimeError):
            pass
