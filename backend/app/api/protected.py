"""Stubs protegidos para validar RBAC (ampliados en C-05/C-06)."""

from fastapi import APIRouter

router = APIRouter(tags=["protected"])


# GET /agenda implementado en app.api.turnos (C-07).

# POST /turnos implementado en app.api.turnos (C-05).
