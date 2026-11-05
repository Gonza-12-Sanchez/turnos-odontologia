"""Repositorio de Paciente."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.paciente import Paciente
from app.repositories.base_repository import BaseRepository


class PacienteRepository(BaseRepository[Paciente]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Paciente)

    async def get_by_usuario_id(self, usuario_id: uuid.UUID) -> Paciente | None:
        stmt = select(Paciente).where(Paciente.usuario_id == usuario_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get(self, entity_id: uuid.UUID) -> Paciente | None:  # type: ignore[override]
        return await super().get(entity_id)
