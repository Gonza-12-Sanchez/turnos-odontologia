"""BaseRepository[T] genérico sobre AsyncSession."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class BaseRepository(Generic[T]):
    def __init__(self, session: AsyncSession, model: type[T]) -> None:
        self.session = session
        self.model = model

    async def get(self, entity_id: UUID) -> T | None:
        return await self.session.get(self.model, entity_id)

    async def add(self, entity: T) -> T:
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def soft_delete(self, entity: T) -> None:
        entity.is_active = False  # type: ignore[attr-defined]
        entity.deleted_at = datetime.now(timezone.utc)  # type: ignore[attr-defined]
        await self.session.flush()