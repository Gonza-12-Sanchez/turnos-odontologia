"""API de disponibilidad y reserva (C-05)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.api.deps import get_db, require_role
from app.models import Usuario
from app.repositories.paciente_repository import PacienteRepository
from app.repositories.unit_of_work import UnitOfWork
from app.schemas.turnos import HorarioLibreOut, TurnoCreate, TurnoOut
from app.services.disponibilidad_service import DisponibilidadService
from app.services.reserva_service import (
    DepositoRequerido,
    ReservaConflicto,
    ReservaService,
)

router = APIRouter(tags=["turnos"])


@router.get("/horarios-libres", response_model=list[HorarioLibreOut])
async def horarios_libres(
    tratamiento: Annotated[UUID, Query()],
    fecha: Annotated[str, Query()],
    sillon: Annotated[UUID | None, Query()] = None,
    db: AsyncSession = Depends(get_db),
):
    service = DisponibilidadService(db)
    return await service.libres(fecha, tratamiento, sillon)


@router.post("/turnos", status_code=status.HTTP_201_CREATED)
async def crear_turno(
    payload: TurnoCreate,
    user: Annotated[Usuario, Depends(require_role("paciente"))],
    db: AsyncSession = Depends(get_db),
):
    uow = UnitOfWork(deps.get_session_factory())
    async with uow:
        paciente = await PacienteRepository(uow.session).get_by_usuario_id(user.id)
        if paciente is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")
        service = ReservaService(uow.session)
        try:
            turno = await service.reservar(payload, paciente, uow)
        except DepositoRequerido as exc:
            return JSONResponse(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                content={"detail": "Seña requerida", "checkout": exc.checkout},
            )
        except ReservaConflicto as exc:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "detail": "Hueco no disponible",
                    "alternativas": [a.model_dump(mode="json") for a in exc.alternativas],
                },
            )
        return TurnoOut.model_validate(turno)