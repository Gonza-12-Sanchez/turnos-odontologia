"""Mutaciones del catálogo y sus eventos comparten una UnitOfWork."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.models import Bloqueo, ConfigAudit, Consultorio, Sillon, Tratamiento
from app.repositories.catalog_repository import CatalogRepository
from app.repositories.unit_of_work import UnitOfWork
from app.schemas.config import (
    ActivityPatch,
    BloqueoCreate,
    BloqueoOut,
    ConfigWarning,
    Page,
    SillonCreate,
    SillonOut,
    TratamientoCreate,
    TratamientoOut,
)

CATALOG = {
    "sillon": (Sillon, SillonCreate, SillonOut),
    "tratamiento": (Tratamiento, TratamientoCreate, TratamientoOut),
    "bloqueo": (Bloqueo, BloqueoCreate, BloqueoOut),
}


class ConfigService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow
        self.session = uow.session

    def repository(self, resource: str):
        return CatalogRepository(self.session, CATALOG[resource][0])

    async def get(self, resource: str, entity_id: UUID):
        entity = await self.repository(resource).get(entity_id)
        if entity is None:
            raise HTTPException(404, "Recurso inexistente")
        return await self.output(resource, entity)

    async def page(self, resource: str, page: int, page_size: int, activo: bool):
        items, total = await self.repository(resource).page(page, page_size, activo)
        return Page(
            items=[await self.output(resource, item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def references(self, resource: str, values: dict, changed: set[str]):
        if resource == "sillon" and "consultorio_id" in changed:
            consultorio = await self.session.get(Consultorio, values["consultorio_id"])
            if consultorio is None:
                raise HTTPException(404, "Consultorio inexistente")
            if not consultorio.is_active:
                raise HTTPException(422, "El consultorio debe estar activo")
        if resource == "bloqueo" and "sillon_id" in changed and values["sillon_id"] is not None:
            sillon = await self.session.get(Sillon, values["sillon_id"])
            if sillon is None:
                raise HTTPException(404, "Sillón inexistente")
            if not sillon.is_active:
                raise HTTPException(422, "El sillón debe estar activo")

    async def output(self, resource: str, entity, *, warnings: bool = False):
        result = CATALOG[resource][2].model_validate(entity)
        if warnings and resource == "bloqueo" and entity.is_active:
            count = await self.repository(resource).overlapping_turnos(entity)
            if count:
                result.warnings = [ConfigWarning(cantidad=count)]
        return result

    async def create(self, resource: str, payload, actor_id: UUID):
        values = payload.model_dump()
        await self.references(resource, values, set(values))
        active = values.pop("activo")
        entity = CATALOG[resource][0](
            **values, is_active=active, deleted_at=None if active else datetime.now(UTC)
        )
        self.session.add(entity)
        return await self.persist(resource, entity, actor_id, "crear", None)

    async def update(self, resource: str, entity_id: UUID, payload, actor_id: UUID):
        entity = await self.repository(resource).get_locked(entity_id)
        if entity is None:
            raise HTTPException(404, "Recurso inexistente")
        before = (await self.output(resource, entity)).model_dump(mode="json", exclude={"warnings"})
        changes = payload.model_dump(exclude_unset=True)
        # Validar el estado combinado también en PATCH de un solo extremo temporal.
        create_schema = CATALOG[resource][1]
        current = {
            key: getattr(entity, "is_active" if key == "activo" else key)
            for key in create_schema.model_fields
        }
        try:
            merged = create_schema.model_validate(current | changes).model_dump()
        except ValidationError as exc:
            raise HTTPException(
                422, exc.errors(include_input=False, include_context=False)
            ) from exc
        await self.references(resource, merged, set(changes))
        action = "actualizar"
        if merged["activo"] != entity.is_active:
            action = "reactivar" if merged["activo"] else "desactivar"
            entity.deleted_at = None if merged["activo"] else datetime.now(UTC)
        effective = False
        for key, value in changes.items():
            attr = "is_active" if key == "activo" else key
            if getattr(entity, attr) != value:
                effective = True
                setattr(entity, attr, value)
        if not effective:
            return await self.output(resource, entity, warnings=True)
        return await self.persist(resource, entity, actor_id, action, before)

    async def delete(self, resource: str, entity_id: UUID, actor_id: UUID):
        # Mismo camino transaccional que PATCH; evita duplicar reglas de baja/auditoría.
        await self.update(resource, entity_id, ActivityPatch(activo=False), actor_id)

    async def persist(self, resource: str, entity, actor_id: UUID, action: str, before):
        try:
            await self.session.flush()
            await self.session.refresh(entity)
            result = await self.output(resource, entity, warnings=True)
            after = result.model_dump(mode="json", exclude={"warnings"})
            self.session.add(
                ConfigAudit(
                    actor_id=actor_id,
                    recurso=resource,
                    recurso_id=entity.id,
                    accion=action,
                    antes=before,
                    despues=after,
                )
            )
            await self.uow.commit()
        except IntegrityError as exc:
            await self.uow.rollback()
            raise HTTPException(409, "Conflicto al guardar configuración") from exc
        return result
