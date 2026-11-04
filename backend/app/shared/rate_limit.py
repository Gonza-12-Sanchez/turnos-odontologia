"""Rate limiting para auth (ventana fija 60s, Redis)."""

from __future__ import annotations

import contextlib
import json

from fastapi import HTTPException, Request, status

from app.db import redis as redis_client


def rate_limit_auth(scope: str):
    async def _dep(request: Request) -> None:
        ip = request.client.host if request.client else "unknown"

        email_norm = "_"
        with contextlib.suppress(ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError):
            body = await request.json()
            if isinstance(body, dict):
                email = body.get("email")
                if email:
                    email_norm = str(email).strip().lower()

        key = f"auth:rl:{scope}:{ip}:{email_norm}"
        count, ttl = await redis_client.consume_auth_attempt(key)

        if count > 5:
            retry_after = ttl if ttl and ttl > 0 else 60
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Demasiados intentos. Reintentá en {retry_after} segundos.",
                headers={"Retry-After": str(retry_after)},
            )

    return _dep
