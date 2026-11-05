"""Consultas comunes del catálogo sobre modelos elegidos por el servidor."""

from uuid import UUID

from sqlalchemy import func, select

from app.models import Turno
from app.repositories.base_repository import BaseRepository


class CatalogRepository[T](BaseRepository[T]):
    async def get_locked(self, entity_id: UUID) -> T | None:
        return await self.session.get(
            self.model, entity_id, with_for_update=True, populate_existing=True
        )

    async def page(self, page: int, page_size: int, activo: bool) -> tuple[list[T], int]:
        predicate = self.model.is_active.is_(activo)
        total = await self.session.scalar(
            select(func.count()).select_from(self.model).where(predicate)
        )
        query = (
            select(self.model)
            .where(predicate)
            .order_by(self.model.created_at, self.model.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = (await self.session.scalars(query)).all()
        return list(items), total

    async def overlapping_turnos(self, bloqueo) -> int:
        query = (
            select(func.count())
            .select_from(Turno)
            .where(
                Turno.is_active.is_(True),
                Turno.estado.notin_(("cancelado", "ausente")),
                Turno.inicio < bloqueo.hasta,
                Turno.fin > bloqueo.desde,
            )
        )
        if bloqueo.sillon_id is not None:
            query = query.where(Turno.sillon_id == bloqueo.sillon_id)
        return await self.session.scalar(query)
