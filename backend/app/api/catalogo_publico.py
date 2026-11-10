"""Catálogo público de recursos activos (C-10): lectura anónima sin auth."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models import Sillon, Tratamiento
from app.schemas.catalogo_publico import (
    CatalogoPublicoOut,
    SillonPublicoOut,
    TratamientoPublicoOut,
)

router = APIRouter(tags=["catalogo-publico"])


@router.get("/catalogo-publico", response_model=CatalogoPublicoOut)
async def catalogo_publico(db: Annotated[AsyncSession, Depends(get_db)]):
    """Devuelve sillones y tratamientos activos para filtros públicos.

    No requiere autenticación. Solo recursos activos, orden estable por nombre/id.
    Sin campos administrativos, pacientes ni precio de referencia.
    """
    sillones_query = (
        select(Sillon)
        .where(Sillon.is_active.is_(True))  # type: ignore[attr-defined]
        .order_by(Sillon.nombre, Sillon.id)  # type: ignore[attr-defined]
    )
    sillones = (await db.scalars(sillones_query)).all()

    tratamientos_query = (
        select(Tratamiento)
        .where(Tratamiento.is_active.is_(True))  # type: ignore[attr-defined]
        .order_by(Tratamiento.nombre, Tratamiento.id)  # type: ignore[attr-defined]
    )
    tratamientos = (await db.scalars(tratamientos_query)).all()

    return CatalogoPublicoOut(
        sillones=[SillonPublicoOut.model_validate(s) for s in sillones],
        tratamientos=[TratamientoPublicoOut.model_validate(t) for t in tratamientos],
    )
