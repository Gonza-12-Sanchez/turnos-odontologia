"""GET /api/health — contrato specs/platform/health/spec.md.

Checks inyectables por módulo (check_db/check_redis) para testear los
4 escenarios sin infraestructura real. El endpoint es público: sin auth.
"""

import asyncio
from collections.abc import Awaitable, Callable

from fastapi import APIRouter
from pydantic import BaseModel
from redis import exceptions as redis_exceptions
from sqlalchemy import exc as sa_exceptions

from app.db import engine as db_engine
from app.db import redis as redis_client
from app.shared.logging import get_logger
from app.shared.settings import settings

logger = get_logger(__name__)

router = APIRouter(tags=["platform"])

CheckFn = Callable[[], Awaitable[str]]


class HealthResponse(BaseModel):
    status: str
    checks: dict[str, str]


async def _bounded(check: CheckFn, name: str) -> str:
    try:
        async with asyncio.timeout(settings.health_check_timeout_seconds):
            return await check()
    except (
        TimeoutError,
        ConnectionError,
        OSError,
        sa_exceptions.SQLAlchemyError,
        redis_exceptions.RedisError,
    ) as exc:
        logger.warning("health check %s down: %s", name, exc)
        return "down"


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    db, red = await asyncio.gather(
        _bounded(db_engine.check_db, "db"),
        _bounded(redis_client.check_redis, "redis"),
    )
    checks = {"db": db, "redis": red}
    status = "ok" if all(v == "up" for v in checks.values()) else "degraded"
    return HealthResponse(status=status, checks=checks)
