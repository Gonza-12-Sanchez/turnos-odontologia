"""Stubs protegidos para validar RBAC (ampliados en C-05/C-06)."""

from fastapi import APIRouter, Depends

from app.api.deps import require_role

router = APIRouter(tags=["protected"])


@router.get("/agenda")
async def agenda(user=Depends(require_role("odontologo", "secretaria"))):
    return {"items": []}


# POST /turnos implementado en app.api.turnos (C-05).
