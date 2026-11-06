"""Servicio de persistencia de RecordatorioWA (C-08)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import RecordatorioWA


class RecordatorioWAService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def registrar_envio(
        self, turno_id: Any, plantilla: str, message_id: str | None, estado: str = "enviado"
    ) -> RecordatorioWA:
        rec = RecordatorioWA(
            turno_id=turno_id,
            tipo="recordatorio",
            plantilla=plantilla,
            message_id=message_id,
            estado=estado,
            respuesta=None,
        )
        self.session.add(rec)
        await self.session.flush()
        await self.session.refresh(rec)
        return rec

    async def registrar_respuesta(
        self, message_id: str, respuesta: str, turno_id: Any = None
    ) -> RecordatorioWA:
        # buscar por message_id
        rec = await self.get_by_message_id(message_id)
        if rec is not None:
            if rec.respuesta is None:
                rec.respuesta = respuesta
                rec.estado = "respondido"
                await self.session.flush()
                await self.session.refresh(rec)
            return rec
        # crear huérfano
        tid = turno_id
        if tid is None:
            # no se puede crear sin turno; devolver None-like impossible -> create placeholder requires turno
            raise ValueError("turno_id requerido para crear RecordatorioWA huérfano")
        rec = RecordatorioWA(
            turno_id=tid,
            tipo="confirmacion",
            plantilla=settings.whatsapp_template_name,
            message_id=message_id,
            estado="respondido",
            respuesta=respuesta,
        )
        self.session.add(rec)
        await self.session.flush()
        await self.session.refresh(rec)
        return rec

    async def get_by_message_id(self, message_id: str) -> RecordatorioWA | None:
        stmt = select(RecordatorioWA).where(RecordatorioWA.message_id == message_id)
        result = await self.session.scalars(stmt)
        return result.first()

    async def get_by_turno_id(self, turno_id: Any) -> list[RecordatorioWA]:
        stmt = select(RecordatorioWA).where(RecordatorioWA.turno_id == turno_id)
        result = await self.session.scalars(stmt)
        return list(result.all())
