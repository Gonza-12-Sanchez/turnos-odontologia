"""API de seña MP y checkout (C-09)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_role
from app.models import IntentoSena, Usuario
from app.repositories.paciente_repository import PacienteRepository
from app.schemas.sena import CheckoutOut, IntentoSenaCreate, IntentoSenaOut
from app.services.sena_service import SenaError, SenaService

router = APIRouter(tags=["sena"])


def sena_service(db: Annotated[AsyncSession, Depends(get_db)]) -> SenaService:
    return SenaService(db)


Service = Annotated[SenaService, Depends(sena_service)]


@router.post(
    "/pagos/sena",
    response_model=CheckoutOut,
    status_code=status.HTTP_201_CREATED,
)
async def crear_sena(
    payload: IntentoSenaCreate,
    user: Annotated[Usuario, Depends(require_role("paciente"))],
    service: Service,
    idempotency_key: Annotated[str, Header()],
    db: AsyncSession = Depends(get_db),
):
    paciente = await PacienteRepository(db).get_by_usuario_id(user.id)
    if paciente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")
    try:
        checkout, is_replay = await service.crear_intento(
            paciente_id=paciente.id,
            sillon_id=payload.sillon_id,
            tratamiento_id=payload.tratamiento_id,
            inicio=payload.inicio,
            idempotency_key=idempotency_key,
        )
        await db.commit()
        if is_replay:
            return JSONResponse(status_code=status.HTTP_200_OK, content=checkout)
        return checkout
    except SenaError:
        await db.rollback()
        raise


@router.get("/pagos/sena/{intento_id}", response_model=IntentoSenaOut)
async def obtener_sena(
    intento_id: UUID,
    user: Annotated[Usuario, Depends(require_role("paciente"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    intento = await db.get(IntentoSena, intento_id)
    if intento is None or not intento.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intento inexistente")
    paciente = await PacienteRepository(db).get_by_usuario_id(user.id)
    if paciente is None or intento.paciente_id != paciente.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intento inexistente")
    return intento
