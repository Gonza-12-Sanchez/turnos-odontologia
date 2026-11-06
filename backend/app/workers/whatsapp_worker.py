"""Worker async de notificaciones WhatsApp (C-08)."""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db import redis as redis_client
from app.models import Turno
from app.services.recordatorio_wa_service import RecordatorioWAService
from app.services.whatsapp_provider import get_whatsapp_provider

logger = logging.getLogger(__name__)

QUEUE = "wa:reminders"
MAX_ATTEMPTS = 5
BACKOFF = [1, 2, 4, 8, 16]


async def process_one(turno_id: str, session: AsyncSession) -> bool:
    """Procesa un turno: envía plantilla y persiste. Retorna True si ok."""
    provider = get_whatsapp_provider()
    plantilla = settings.whatsapp_template_name
    # load turno
    turno = await session.get(Turno, turno_id)
    if turno is None:
        logger.warning("Turno %s no encontrado, descartando job", turno_id)
        return True
    svc = RecordatorioWAService(session)
    try:
        message_id = await provider.send_template(turno, plantilla)
        await svc.registrar_envio(turno.id, plantilla, message_id, estado="enviado")
        await session.commit()
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Fallo envío WA turno %s: %s", turno_id, exc)
        try:
            await svc.registrar_envio(turno.id, plantilla, None, estado="fallido")
            await session.commit()
        except Exception:  # noqa: BLE001
            await session.rollback()
        return False


async def _attempts_key(turno_id: str) -> str:
    return f"wa:reminder:attempts:{turno_id}"


async def run_worker() -> None:
    engine = create_async_engine(
        settings.database_url
        if hasattr(settings, "database_url")
        else "postgresql+asyncpg://turnos:turnos@localhost:5432/turnos",
        pool_pre_ping=True,
    )
    # Use TEST_DATABASE_URL override? worker uses settings.database_url
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    redis = redis_client.get_redis()
    logger.info("WhatsApp worker iniciado, consumiendo %s", QUEUE)
    while True:
        try:
            item = await redis.brpop(QUEUE, timeout=5)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis brpop error: %s", exc)
            await asyncio.sleep(2)
            continue
        if item is None:
            continue
        _, turno_id = item
        turno_id = turno_id if isinstance(turno_id, str) else turno_id.decode()
        # attempts
        key = await _attempts_key(turno_id)
        try:
            attempts = int(await redis.get(key) or 0)
        except Exception:  # noqa: BLE001
            attempts = 0
        attempts += 1
        try:
            await redis.set(key, str(attempts), ex=3600)
        except Exception:  # noqa: BLE001, S110
            pass

        async with session_factory() as session:
            ok = await process_one(turno_id, session)

        if ok:
            try:
                await redis.delete(key)
            except Exception:  # noqa: BLE001, S110
                pass
            continue
        # failure: retry or give up
        if attempts >= MAX_ATTEMPTS:
            logger.error("Turno %s agotó reintentos, marcado fallido", turno_id)
            continue
        backoff = BACKOFF[min(attempts - 1, len(BACKOFF) - 1)]
        await asyncio.sleep(backoff)
        try:
            await redis.lpush(QUEUE, turno_id)
        except Exception:  # noqa: BLE001, S110
            pass


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_worker())
