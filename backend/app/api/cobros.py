"""API de cobros locales (C-09), solo secretaria."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admin
from app.models import Usuario
from app.schemas.cobros import (
    CobroCreate,
    CobroListOut,
)
from app.services.cobro_service import CobroError, CobroService

router = APIRouter(tags=["cobros"], dependencies=[Depends(require_admin())])

Admin = Annotated[Usuario, Depends(require_admin())]


def cobro_service(db: Annotated[AsyncSession, Depends(get_db)]) -> CobroService:
    return CobroService(db)


Service = Annotated[CobroService, Depends(cobro_service)]


@router.post("/cobros", status_code=status.HTTP_201_CREATED)
async def registrar_cobro(
    payload: CobroCreate,
    actor: Admin,
    service: Service,
    db: AsyncSession = Depends(get_db),
    idempotency_key: Annotated[str | None, Header()] = None,
):
    try:
        result, is_replay = await service.registrar(
            turno_id=payload.turno_id,
            monto_centavos=payload.monto_centavos,
            medio=payload.medio,
            tipo=payload.tipo,
            actor_id=actor.id,
            idempotency_key=idempotency_key,
            override_motivo=payload.override_motivo,
        )
        await db.commit()
        http_status = status.HTTP_200_OK if is_replay else status.HTTP_201_CREATED
        return JSONResponse(status_code=http_status, content=result)
    except CobroError:
        await db.rollback()
        raise


@router.get("/cobros", response_model=list[CobroListOut])
async def listar_cobros(
    turno_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    # Proyección simplificada; el acceso ya está acotado por require_admin (secretaria).
    from sqlalchemy import select

    from app.models import Cobro

    stmt = select(Cobro).where(Cobro.is_active.is_(True))
    if turno_id is not None:
        stmt = stmt.where(Cobro.turno_id == turno_id)
    stmt = stmt.order_by(Cobro.created_at)
    rows = (await db.scalars(stmt)).all()
    return [
        CobroListOut(
            id=r.id,
            turno_id=r.turno_id,
            monto_centavos=r.monto_centavos,
            medio=r.medio,
            tipo=r.tipo,
            estado_mp=r.estado_mp,
            referencia_mp=r.referencia_mp,
            created_at=r.created_at.isoformat(),
        )
        for r in rows
    ]
