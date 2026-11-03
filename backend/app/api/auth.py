"""Router de autenticación /auth/*."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.db.engine import get_session_factory
from app.models.usuario import Usuario
from app.repositories.unit_of_work import UnitOfWork
from app.schemas.auth import (
    LoginIn,
    RegistroIn,
    TokenOut,
    UserOut,
)
from app.services.auth_service import AuthService
from app.shared.rate_limit import rate_limit_auth

router = APIRouter(tags=["auth"])


def _access_token_from_request(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    return ""


def _set_refresh_cookie(response: Response, value: str, max_age: int) -> None:
    response.set_cookie(
        key="refresh_token",
        value=value,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/auth",
        max_age=max_age,
    )


@router.post("/registro", status_code=status.HTTP_201_CREATED, response_model=UserOut)
async def registro(
    payload: RegistroIn,
    request: Request,
    _rl=Depends(rate_limit_auth("registro")),
    db: AsyncSession = Depends(get_db),
):
    uow = UnitOfWork(get_session_factory())
    async with uow:
        user = await AuthService(uow).registrar(payload)
    return UserOut(id=user.id, email=user.email, rol=user.rol, telefono=user.telefono)


@router.post("/login", response_model=TokenOut)
async def login(
    payload: LoginIn,
    request: Request,
    response: Response,
    _rl=Depends(rate_limit_auth("login")),
    db: AsyncSession = Depends(get_db),
):
    uow = UnitOfWork(get_session_factory())
    async with uow:
        token_out, refresh_token, refresh_ttl = await AuthService(uow).login(
            payload.email, payload.password
        )
    _set_refresh_cookie(response, refresh_token, refresh_ttl)
    return token_out


@router.post("/refresh", response_model=TokenOut)
async def refresh(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    cookie = request.cookies.get("refresh_token")
    uow = UnitOfWork(get_session_factory())
    async with uow:
        token_out, new_refresh, refresh_ttl = await AuthService(uow).refresh(cookie)
    _set_refresh_cookie(response, new_refresh, refresh_ttl)
    return token_out


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    access_token = _access_token_from_request(request)
    cookie = request.cookies.get("refresh_token")
    uow = UnitOfWork(get_session_factory())
    async with uow:
        await AuthService(uow).logout(access_token, cookie)
    response.delete_cookie("refresh_token", path="/auth")
    return None


@router.get("/me", response_model=UserOut)
async def me(
    request: Request,
    user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    uow = UnitOfWork(get_session_factory())
    async with uow:
        return await AuthService(uow).me(user, uow.session)
