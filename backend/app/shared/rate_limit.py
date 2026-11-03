"""Rate limiting para auth (ventana fija 60s, Redis)."""

from __future__ import annotations

import contextlib
import json

import redis.exceptions
from fastapi import HTTPException, Request, status

from app.db import redis as redis_client


def rate_limit_auth(scope: str):
    async def _dep(request: Request) -> None:
        ip = request.client.host if request.client else "unknown"
        xff = request.headers.get("x-forwarded-for")
        if xff:
            ip = xff.split(",")[0].strip()

        email_norm = "_"
        with contextlib.suppress(ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError):
            body = await request.json()
            if isinstance(body, dict):
                email = body.get("email")
                if email:
                    email_norm = str(email).strip().lower()

        key = f"auth:rl:{scope}:{ip}:{email_norm}"
        try:
            client = redis_client.get_redis()
            count = await client.incr(key)
            if count == 1:
                await client.expire(key, 60)
            ttl = await client.ttl(key)
        except (redis.exceptions.RedisError, RuntimeError, ConnectionError, OSError):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Servicio no disponible",
            )

        if count > 5:
            retry_after = ttl if ttl and ttl > 0 else 60
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Demasiados intentos. Reintentá en {retry_after} segundos.",
                headers={"Retry-After": str(retry_after)},
            )

    return _dep
