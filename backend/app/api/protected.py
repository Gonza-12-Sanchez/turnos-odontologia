"""Stubs protegidos para validar RBAC (ampliados en C-05/C-06)."""

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user, require_role

router = APIRouter(tags=["protected"])


@router.get("/agenda")
async def agenda(user=Depends(require_role("odontologo", "secretaria"))):
    return {"items": []}


@router.post("/turnos", status_code=status.HTTP_201_CREATED)
async def crear_turno(user=Depends(get_current_user)):
    return {"ok": True}
