"""API administrativa de catálogo (C-04), solo secretaria."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from app.api.deps import get_uow, require_admin
from app.models import Usuario
from app.repositories.unit_of_work import UnitOfWork
from app.schemas.config import (
    BloqueoCreate,
    BloqueoOut,
    BloqueoPatch,
    ContextoConsultorioOut,
    Page,
    SillonCreate,
    SillonOut,
    SillonPatch,
    TratamientoCreate,
    TratamientoOut,
    TratamientoPatch,
)
from app.services.config_service import ConfigService

Admin = Annotated[Usuario, Depends(require_admin())]


async def config_service(uow: Annotated[UnitOfWork, Depends(get_uow)]):
    return ConfigService(uow)


Service = Annotated[ConfigService, Depends(config_service)]
router = APIRouter(prefix="/api/config", tags=["config"], dependencies=[Depends(require_admin())])


class Pagination:
    def __init__(
        self,
        page: Annotated[int, Query(ge=1)] = 1,
        page_size: Annotated[int, Query(ge=1, le=100)] = 20,
        activo: bool = True,
    ):
        self.page, self.page_size, self.activo = page, page_size, activo


Paging = Annotated[Pagination, Depends()]


@router.get("/contexto-consultorio", response_model=ContextoConsultorioOut)
async def contexto_consultorio(response: Response, service: Service):
    response.headers["Cache-Control"] = "no-store"
    return await service.contexto_consultorio()


@router.post("/sillones", response_model=SillonOut, status_code=201)
async def create_sillon(payload: SillonCreate, actor: Admin, service: Service):
    return await service.create("sillon", payload, actor.id)


@router.get("/sillones", response_model=Page[SillonOut])
async def list_sillones(service: Service, paging: Paging):
    return await service.page("sillon", paging.page, paging.page_size, paging.activo)


@router.get("/sillones/{entity_id}", response_model=SillonOut)
async def get_sillon(entity_id: UUID, service: Service):
    return await service.get("sillon", entity_id)


@router.patch("/sillones/{entity_id}", response_model=SillonOut)
async def patch_sillon(entity_id: UUID, payload: SillonPatch, actor: Admin, service: Service):
    return await service.update("sillon", entity_id, payload, actor.id)


@router.delete("/sillones/{entity_id}", status_code=204)
async def delete_sillon(entity_id: UUID, actor: Admin, service: Service):
    await service.delete("sillon", entity_id, actor.id)
    return Response(status_code=204)


@router.post("/tratamientos", response_model=TratamientoOut, status_code=201)
async def create_tratamiento(payload: TratamientoCreate, actor: Admin, service: Service):
    return await service.create("tratamiento", payload, actor.id)


@router.get("/tratamientos", response_model=Page[TratamientoOut])
async def list_tratamientos(service: Service, paging: Paging):
    return await service.page("tratamiento", paging.page, paging.page_size, paging.activo)


@router.get("/tratamientos/{entity_id}", response_model=TratamientoOut)
async def get_tratamiento(entity_id: UUID, service: Service):
    return await service.get("tratamiento", entity_id)


@router.patch("/tratamientos/{entity_id}", response_model=TratamientoOut)
async def patch_tratamiento(
    entity_id: UUID, payload: TratamientoPatch, actor: Admin, service: Service
):
    return await service.update("tratamiento", entity_id, payload, actor.id)


@router.delete("/tratamientos/{entity_id}", status_code=204)
async def delete_tratamiento(entity_id: UUID, actor: Admin, service: Service):
    await service.delete("tratamiento", entity_id, actor.id)
    return Response(status_code=204)


@router.post("/bloqueos", response_model=BloqueoOut, status_code=201)
async def create_bloqueo(payload: BloqueoCreate, actor: Admin, service: Service):
    return await service.create("bloqueo", payload, actor.id)


@router.get("/bloqueos", response_model=Page[BloqueoOut])
async def list_bloqueos(service: Service, paging: Paging):
    return await service.page("bloqueo", paging.page, paging.page_size, paging.activo)


@router.get("/bloqueos/{entity_id}", response_model=BloqueoOut)
async def get_bloqueo(entity_id: UUID, service: Service):
    return await service.get("bloqueo", entity_id)


@router.patch("/bloqueos/{entity_id}", response_model=BloqueoOut)
async def patch_bloqueo(entity_id: UUID, payload: BloqueoPatch, actor: Admin, service: Service):
    return await service.update("bloqueo", entity_id, payload, actor.id)


@router.delete("/bloqueos/{entity_id}", status_code=204)
async def delete_bloqueo(entity_id: UUID, actor: Admin, service: Service):
    await service.delete("bloqueo", entity_id, actor.id)
    return Response(status_code=204)
