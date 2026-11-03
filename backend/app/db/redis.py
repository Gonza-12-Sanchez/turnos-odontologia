"""Cliente Redis async (colas y workers en C-08)."""

import redis.asyncio as redis

from app.shared.settings import settings

_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(
            settings.redis_url, decode_responses=True, socket_timeout=2.0
        )
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


# --- helpers de auth (blacklist / familias de refresh) ---


async def blacklist_access(jti: str, ttl_seconds: int) -> None:
    if ttl_seconds and ttl_seconds > 0:
        await get_redis().set(f"auth:blacklist:access:{jti}", "1", ex=ttl_seconds)


async def is_access_blacklisted(jti: str) -> bool:
    return bool(await get_redis().get(f"auth:blacklist:access:{jti}"))


async def blacklist_refresh(jti: str, ttl_seconds: int) -> None:
    if ttl_seconds and ttl_seconds > 0:
        await get_redis().set(f"auth:blacklist:refresh:{jti}", "1", ex=ttl_seconds)


async def is_refresh_blacklisted(jti: str) -> bool:
    return bool(await get_redis().get(f"auth:blacklist:refresh:{jti}"))


async def set_refresh_family(fid: str, jti: str, ttl_seconds: int) -> None:
    await get_redis().set(f"auth:refresh:family:{fid}", jti, ex=ttl_seconds)


async def get_refresh_family(fid: str) -> str | None:
    return await get_redis().get(f"auth:refresh:family:{fid}")


async def delete_refresh_family(fid: str) -> None:
    await get_redis().delete(f"auth:refresh:family:{fid}")
