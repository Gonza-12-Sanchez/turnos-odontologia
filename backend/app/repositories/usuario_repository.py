"""Repositorio de Usuario."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.usuario import Usuario
from app.repositories.base_repository import BaseRepository


class UsuarioRepository(BaseRepository[Usuario]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Usuario)

    async def get_by_email(self, email: str) -> Optional[Usuario]:
        stmt = select(Usuario).where(
            func.lower(Usuario.email) == email.strip().lower()
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_telefono(self, telefono: str) -> Optional[Usuario]:
        stmt = select(Usuario).where(Usuario.telefono == telefono)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get(self, entity_id: uuid.UUID) -> Optional[Usuario]:  # type: ignore[override]
        return await super().get(entity_id)
