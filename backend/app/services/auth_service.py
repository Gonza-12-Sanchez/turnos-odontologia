"""Servicio de autenticación (registro, login, refresh, logout, me)."""

from __future__ import annotations

import logging
import math
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool
from jose import JWTError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db import redis as redis_client
from app.models.paciente import Paciente
from app.models.usuario import Usuario
from app.repositories.paciente_repository import PacienteRepository
from app.repositories.unit_of_work import UnitOfWork
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.auth import TokenOut, UserOut
from app.shared.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    password_needs_rehash,
    verify_password,
)

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    @property
    def session(self) -> AsyncSession:
        return self.uow.session

    async def registrar(self, payload) -> Usuario:
        user_repo = UsuarioRepository(self.session)
        pac_repo = PacienteRepository(self.session)

        existing_email = await user_repo.get_by_email(payload.email)
        if existing_email is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email ya registrado")

        existing_tel = await user_repo.get_by_telefono(payload.telefono)
        if existing_tel is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Teléfono ya registrado"
            )

        hashed = await run_in_threadpool(hash_password, payload.password)

        user = Usuario(
            email=payload.email,
            telefono=payload.telefono,
            password_hash=hashed,
            rol="paciente",
        )
        try:
            await user_repo.add(user)
            paciente = Paciente(
                usuario_id=user.id,
                nombre=payload.nombre,
                telefono=payload.telefono,
                obra_social=payload.obra_social,
            )
            await pac_repo.add(paciente)
            await self.uow.commit()
        except IntegrityError:
            await self.uow.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Conflicto de unicidad"
            )

        return user

    async def login(self, email: str, password: str) -> tuple[TokenOut, str, int]:
        user_repo = UsuarioRepository(self.session)
        user = await user_repo.get_by_email(email)

        ok = False
        if user is not None:
            ok = await run_in_threadpool(verify_password, password, user.password_hash)

        if user is None or not user.is_active or not ok:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas",
            )

        if password_needs_rehash(user.password_hash):
            user.password_hash = await run_in_threadpool(hash_password, password)
            await self.uow.commit()

        access_token, _access_jti, _access_ttl = create_access_token(
            user.id, [user.rol], user.email
        )
        fid = str(uuid.uuid4())
        refresh_token, _refresh_jti, refresh_ttl = create_refresh_token(user.id, fid)

        await redis_client.set_refresh_family(fid, _refresh_jti, refresh_ttl)

        token_out = TokenOut(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.jwt_expire_minutes * 60,
        )
        return token_out, refresh_token, refresh_ttl

    async def refresh(self, refresh_cookie: str | None) -> tuple[TokenOut, str, int]:
        if not refresh_cookie:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh ausente")

        try:
            payload = decode_token(refresh_cookie)
        except (JWTError, ValueError, TypeError):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh inválido")

        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh inválido")

        jti = payload.get("jti")
        fid = payload.get("fid")
        sub = payload.get("sub")
        exp = payload.get("exp")
        if not jti or not fid or not sub:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh inválido")

        user_repo = UsuarioRepository(self.session)
        try:
            uid = uuid.UUID(str(sub))
        except (ValueError, TypeError):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh inválido")
        user = await user_repo.get(uid)
        if user is None or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario inactivo")

        access_token, _access_jti, _access_ttl = create_access_token(
            user.id, [user.rol], user.email
        )
        new_refresh, new_refresh_jti, new_refresh_ttl = create_refresh_token(user.id, fid)
        remaining = max(0, math.ceil(exp - datetime.now(UTC).timestamp()))
        rotated = await redis_client.rotate_refresh(
            fid,
            jti,
            new_refresh_jti,
            remaining,
            new_refresh_ttl,
        )
        if rotated != 1:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh reutilizado" if rotated == -1 else "Refresh inválido",
            )

        token_out = TokenOut(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.jwt_expire_minutes * 60,
        )
        return token_out, new_refresh, new_refresh_ttl

    async def logout(self, access_token: str | None, refresh_cookie: str | None) -> None:
        now = datetime.now(UTC)

        if access_token:
            try:
                payload = decode_token(access_token)
                jti = payload.get("jti")
                exp = payload.get("exp")
                remaining = 0
                if exp is not None:
                    remaining = math.ceil(float(exp) - now.timestamp())
                remaining = max(remaining, 0)
                if jti:
                    await redis_client.blacklist_access(jti, remaining)
            except (JWTError, ValueError, TypeError) as exc:
                logger.debug("Error procesando access token en logout: %s", exc)

        if refresh_cookie:
            try:
                payload = decode_token(refresh_cookie)
                rjti = payload.get("jti")
                fid = payload.get("fid")
                exp = payload.get("exp")
                remaining = 0
                if exp is not None:
                    remaining = math.ceil(float(exp) - now.timestamp())
                remaining = max(remaining, 0)
                if rjti:
                    await redis_client.blacklist_refresh(rjti, remaining)
                if fid:
                    await redis_client.delete_refresh_family(fid)
            except (JWTError, ValueError, TypeError) as exc:
                logger.debug("Error procesando refresh token en logout: %s", exc)

    async def me(self, user: Usuario, session: AsyncSession | None = None) -> UserOut:
        nombre = None
        telefono = user.telefono
        if user.rol == "paciente":
            sess = session or self.session
            pac_repo = PacienteRepository(sess)
            pac = await pac_repo.get_by_usuario_id(user.id)
            if pac is not None:
                nombre = pac.nombre
                telefono = pac.telefono
        return UserOut(
            id=user.id,
            email=user.email,
            rol=user.rol,
            nombre=nombre,
            telefono=telefono,
        )
