"""Cliente Redis async (colas y workers en C-08)."""

import redis.asyncio as redis

from app.shared.settings import settings

_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(settings.redis_url, decode_responses=True)
    return _client


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def check_redis() -> str:
    """PING a Redis. Devuelve 'up' o lanza excepción."""
    client = get_redis()
    await client.ping()
    return "up"
