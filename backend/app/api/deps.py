"""Dependencias FastAPI: sesion DB, auth y RBAC."""

from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import redis as redis_client
from app.db.engine import get_session_factory
from app.models.usuario import Usuario
from app.repositories.usuario_repository import UsuarioRepository
from app.shared.security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)


async def get_db() -> AsyncSession:
    factory = get_session_factory()
    async with factory() as session:
        yield session


async def _load_user_from_token(token: str, db: AsyncSession) -> Usuario:
    try:
        payload = decode_token(token)
    except (JWTError, ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    jti = payload.get("jti")
    if jti and await redis_client.is_access_blacklisted(jti):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revocado")
    sub = payload.get("sub")
    try:
        uid = uuid.UUID(str(sub))
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    user = await UsuarioRepository(db).get(uid)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario inactivo")
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Usuario:
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")
    return await _load_user_from_token(credentials.credentials, db)


def require_role(*roles: str):
    async def _dep(user: Usuario = Depends(get_current_user)) -> Usuario:
        if user.rol not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
        return user

    return _dep


def require_admin():
    return require_role("secretaria")


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Usuario | None:
    if credentials is None or not credentials.credentials:
        return None
    try:
        return await _load_user_from_token(credentials.credentials, db)
    except HTTPException:
        return None
