"""Seguridad: hashing (passlib bcrypt) y JWT (jose HS256)."""

from __future__ import annotations

import datetime
import uuid
from typing import Any

import bcrypt
from fastapi.concurrency import run_in_threadpool
from jose import jwt

from app.core.config import settings

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=settings.bcrypt_rounds)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


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
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])


__all__ = [
    "ALGORITHM",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "hash_password",
    "run_in_threadpool",
    "verify_password",
]
