"""API de disponibilidad y reserva (C-05)."""

from __future__ import annotations

from datetime import date
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
from app.schemas.turnos import (
    AgendaSillonOut,
    GestionTurnoPatch,
    HorarioLibreOut,
    MarcarAsistenciaIn,
    MisReservaOut,
    ReprogramarIn,
    SobreturnoIn,
    TurnoCreate,
    TurnoOut,
)
from app.services.agenda_lectura_service import AgendaLecturaService
from app.services.disponibilidad_service import DisponibilidadService
from app.services.gestion_turnos_service import GestionTurnosService
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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado"
            )
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


@router.patch("/turnos/{turno_id}/confirmar", response_model=TurnoOut)
async def confirmar_turno(
    turno_id: UUID,
    user: Annotated[Usuario, Depends(require_role("secretaria", "paciente"))],
    db: AsyncSession = Depends(get_db),
):
    uow = UnitOfWork(deps.get_session_factory())
    async with uow:
        service = GestionTurnosService(uow.session)
        turno = await service.confirmar(turno_id, user)
        return TurnoOut.model_validate(turno)


@router.patch("/turnos/{turno_id}/cancelar", response_model=TurnoOut)
async def cancelar_turno(
    turno_id: UUID,
    user: Annotated[Usuario, Depends(require_role("secretaria", "paciente"))],
    db: AsyncSession = Depends(get_db),
):
    uow = UnitOfWork(deps.get_session_factory())
    async with uow:
        service = GestionTurnosService(uow.session)
        turno = await service.cancelar(turno_id, user)
        return TurnoOut.model_validate(turno)


@router.patch("/turnos/{turno_id}/reprogramar")
async def reprogramar_turno(
    turno_id: UUID,
    payload: ReprogramarIn,
    user: Annotated[Usuario, Depends(require_role("secretaria", "paciente"))],
    db: AsyncSession = Depends(get_db),
):
    uow = UnitOfWork(deps.get_session_factory())
    async with uow:
        service = GestionTurnosService(uow.session)
        try:
            turno = await service.reprogramar(turno_id, payload.inicio, payload.sillon_id, user)
        except ReservaConflicto as exc:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "detail": "Hueco no disponible",
                    "alternativas": [a.model_dump(mode="json") for a in exc.alternativas],
                },
            )
        return TurnoOut.model_validate(turno)


@router.patch("/turnos/{turno_id}/marcar-asistencia", response_model=TurnoOut)
async def marcar_asistencia(
    turno_id: UUID,
    payload: MarcarAsistenciaIn,
    user: Annotated[Usuario, Depends(require_role("secretaria", "odontologo"))],
    db: AsyncSession = Depends(get_db),
):
    uow = UnitOfWork(deps.get_session_factory())
    async with uow:
        service = GestionTurnosService(uow.session)
        turno = await service.marcar_asistencia(turno_id, payload.estado, user)
        return TurnoOut.model_validate(turno)


@router.patch("/turnos/{turno_id}/sobreturno", response_model=TurnoOut)
async def marcar_sobreturno(
    turno_id: UUID,
    payload: SobreturnoIn,
    user: Annotated[Usuario, Depends(require_role("secretaria"))],
    db: AsyncSession = Depends(get_db),
):
    uow = UnitOfWork(deps.get_session_factory())
    async with uow:
        service = GestionTurnosService(uow.session)
        turno = await service.sobreturno(turno_id, payload.motivo, user)
        return TurnoOut.model_validate(turno)


@router.patch("/turnos/{turno_id}", response_model=TurnoOut)
async def patch_turno(
    turno_id: UUID,
    payload: GestionTurnoPatch,
    user: Annotated[Usuario, Depends(require_role("secretaria", "paciente", "odontologo"))],
    db: AsyncSession = Depends(get_db),
):
    uow = UnitOfWork(deps.get_session_factory())
    async with uow:
        service = GestionTurnosService(uow.session)
        turno = await service.patch(
            turno_id,
            es_sobreturno=payload.es_sobreturno,
            motivo_sobreturno=payload.motivo_sobreturno,
            origen=payload.origen,
            actor=user,
        )
        return TurnoOut.model_validate(turno)


@router.get("/agenda", response_model=list[AgendaSillonOut])
async def agenda(
    fecha: Annotated[date, Query()],
    user: Annotated[Usuario, Depends(require_role("odontologo", "secretaria"))],
    db: AsyncSession = Depends(get_db),
    sillon: Annotated[UUID | None, Query()] = None,
    sillon_id: Annotated[UUID | None, Query()] = None,
    estado: Annotated[str | None, Query()] = None,
):
    sid = sillon if sillon is not None else sillon_id
    service = AgendaLecturaService(db)
    return await service.agenda(fecha, sid, estado)


@router.get("/mis-reservas", response_model=list[MisReservaOut])
async def mis_reservas(
    user: Annotated[Usuario, Depends(require_role("paciente"))],
    db: AsyncSession = Depends(get_db),
    desde: Annotated[date | None, Query()] = None,
    hasta: Annotated[date | None, Query()] = None,
    estado: Annotated[str | None, Query()] = None,
):
    paciente = await PacienteRepository(db).get_by_usuario_id(user.id)
    if paciente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")
    service = AgendaLecturaService(db)
    return await service.mis_reservas(paciente, desde, hasta, estado)
