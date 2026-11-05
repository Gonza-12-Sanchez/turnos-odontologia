"""Seguridad: bcrypt directo y validación estricta de JWT HS256."""

from __future__ import annotations

import datetime
import uuid
from typing import Any

import bcrypt
from fastapi.concurrency import run_in_threadpool
from jose import JWTError, jwt

from app.core.config import settings

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    if len(password.encode("utf-8")) > 72:
        raise ValueError("La contraseña no puede superar 72 bytes UTF-8")
    salt = bcrypt.gensalt(rounds=settings.bcrypt_rounds)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    if len(plain.encode("utf-8")) > 72:
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def password_needs_rehash(hashed: str) -> bool:
    """Actualizar solo costos menores; nunca degradar un hash más fuerte."""
    return int(hashed.split("$")[2]) < settings.bcrypt_rounds


def create_access_token(user_id: Any, roles: list[str], email: str | None) -> tuple[str, str, int]:
    now = datetime.datetime.now(datetime.UTC)
    jti = str(uuid.uuid4())
    expire = now + datetime.timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": str(user_id),
        "roles": roles,
        "email": email,
        "jti": jti,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=ALGORITHM)
    ttl = int((expire - now).total_seconds())
    return token, jti, ttl


def create_refresh_token(user_id: Any, fid: str) -> tuple[str, str, int]:
    now = datetime.datetime.now(datetime.UTC)
    jti = str(uuid.uuid4())
    expire = now + datetime.timedelta(days=settings.refresh_expire_days)
    payload = {
        "sub": str(user_id),
        "roles": [],
        "email": None,
        "jti": jti,
        "type": "refresh",
        "fid": fid,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=ALGORITHM)
    ttl = int((expire - now).total_seconds())
    return token, jti, ttl


def decode_token(token: str) -> dict[str, Any]:
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
    required = {"sub", "roles", "email", "jti", "type", "iat", "exp"}
    if not required <= payload.keys():
        raise JWTError("Claims obligatorios ausentes")
    kind = payload["type"]
    if kind not in {"access", "refresh"}:
        raise JWTError("Tipo de token inválido")
    identifiers = ["sub", "jti"] + (["fid"] if kind == "refresh" else [])
    for key in identifiers:
        value = payload.get(key)
        if not isinstance(value, str):
            raise JWTError("Identificador inválido")
        try:
            uuid.UUID(value)
        except ValueError as exc:
            raise JWTError("Identificador inválido") from exc
    roles = payload["roles"]
    if not isinstance(roles, list) or any(
        not isinstance(role, str) or role not in {"paciente", "odontologo", "secretaria"}
        for role in roles
    ):
        raise JWTError("Roles inválidos")
    if (kind == "access" and not roles) or (kind == "refresh" and roles):
        raise JWTError("Roles incompatibles con tipo de token")
    email = payload["email"]
    if email is not None and not isinstance(email, str):
        raise JWTError("Email inválido")
    if kind == "refresh" and email is not None:
        raise JWTError("Email incompatible con refresh")
    iat, exp = payload["iat"], payload["exp"]
    now = int(datetime.datetime.now(datetime.UTC).timestamp())
    if type(iat) is not int or type(exp) is not int:  # noqa: E721
        raise JWTError("Tiempos inválidos")
    if not 0 <= iat <= now or exp <= now or exp <= iat:
        raise JWTError("Tiempos incoherentes")
    return payload


__all__ = [
    "ALGORITHM",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "hash_password",
    "run_in_threadpool",
    "verify_password",
]
