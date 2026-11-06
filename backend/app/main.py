"""Turnos Odontología API — application factory (routers por change)."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.auth import router as auth_router
from app.api.config import router as config_router
from app.api.health import router as health_router
from app.api.protected import router as protected_router
from app.api.turnos import router as turnos_router
from app.api.webhooks import router as webhooks_router
from app.core.config import settings
from app.db import engine as db_engine
from app.db import redis as redis_client
from app.shared.exceptions import AuthStorageUnavailable
from app.shared.logging import get_logger

logger = get_logger(__name__)


def _is_prod() -> bool:
    import os

    env = (
        getattr(settings, "environment", None)
        or os.getenv("ENV")
        or os.getenv("ENVIRONMENT")
        or os.getenv("APP_ENV")
        or ""
    ).lower()
    if env in {"prod", "production"}:
        return True
    debug_env = os.getenv("DEBUG")
    if debug_env is not None and debug_env.lower() in {"0", "false", "no"}:
        return True
    return getattr(settings, "debug", True) is False


def validate_jwt_secret() -> None:
    secret = settings.jwt_secret_key
    invalid = secret == "CHANGE-ME" or len(secret) < 32
    if not invalid:
        return
    if _is_prod():
        raise RuntimeError("JWT_SECRET_KEY inválido o placeholder en producción")
    logger.warning("JWT_SECRET_KEY inválido o placeholder (modo dev); no usar en producción")


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_jwt_secret()
    yield
    await redis_client.close_redis()
    await db_engine.dispose_engine()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response


def create_app() -> FastAPI:
    app = FastAPI(title="turnos-odontologia", version="0.1.0", lifespan=lifespan)

    @app.exception_handler(AuthStorageUnavailable)
    async def auth_storage_unavailable(request: Request, exc: AuthStorageUnavailable):
        return JSONResponse(status_code=503, content={"detail": "Servicio no disponible"})

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.include_router(health_router, prefix="/api")
    app.include_router(auth_router, prefix="/auth")
    app.include_router(config_router)
    app.include_router(protected_router)
    app.include_router(turnos_router)
    app.include_router(webhooks_router, prefix="/webhooks")
    return app


app = create_app()
