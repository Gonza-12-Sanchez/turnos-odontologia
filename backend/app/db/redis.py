"""Cliente Redis async (colas y workers en C-08)."""

import redis.asyncio as redis
from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from app.shared.exceptions import AuthStorageUnavailable
from app.shared.settings import settings

_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_timeout=2.0,
            socket_connect_timeout=2.0,
            retry=Retry(NoBackoff(), 0),
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


async def _auth_execute(*args):
    try:
        return await get_redis().execute_command(*args)
    except (RedisConnectionError, RedisTimeoutError, OSError) as exc:
        raise AuthStorageUnavailable() from exc


async def blacklist_access(jti: str, ttl_seconds: int) -> None:
    if ttl_seconds and ttl_seconds > 0:
        await _auth_execute("SET", f"auth:blacklist:access:{jti}", "1", "EX", ttl_seconds)


async def is_access_blacklisted(jti: str) -> bool:
    return bool(await _auth_execute("GET", f"auth:blacklist:access:{jti}"))


async def blacklist_refresh(jti: str, ttl_seconds: int) -> None:
    if ttl_seconds and ttl_seconds > 0:
        await _auth_execute("SET", f"auth:blacklist:refresh:{jti}", "1", "EX", ttl_seconds)


async def is_refresh_blacklisted(jti: str) -> bool:
    return bool(await _auth_execute("GET", f"auth:blacklist:refresh:{jti}"))


async def set_refresh_family(fid: str, jti: str, ttl_seconds: int) -> None:
    await _auth_execute("SET", f"auth:refresh:family:{fid}", jti, "EX", ttl_seconds)


async def get_refresh_family(fid: str) -> str | None:
    return await _auth_execute("GET", f"auth:refresh:family:{fid}")


async def delete_refresh_family(fid: str) -> None:
    await _auth_execute("DEL", f"auth:refresh:family:{fid}")


_ROTATE_REFRESH = """
if redis.call('EXISTS', KEYS[1]) == 1 then
    redis.call('DEL', KEYS[2])
    return -1
end
if redis.call('GET', KEYS[2]) ~= ARGV[1] then return 0 end
if tonumber(ARGV[3]) <= 0 then return 0 end
redis.call('SET', KEYS[1], '1', 'EX', ARGV[3])
redis.call('SET', KEYS[2], ARGV[2], 'EX', ARGV[4])
return 1
"""


async def rotate_refresh(
    fid: str,
    old_jti: str,
    new_jti: str,
    remaining: int,
    new_ttl: int,
) -> int:
    """1=rotado, 0=inválido, -1=reuso; no resucita familias eliminadas."""
    return int(
        await _auth_execute(
            "EVAL",
            _ROTATE_REFRESH,
            2,
            f"auth:blacklist:refresh:{old_jti}",
            f"auth:refresh:family:{fid}",
            old_jti,
            new_jti,
            remaining,
            new_ttl,
        )
    )


_RATE_LIMIT = """
local count = redis.call('INCR', KEYS[1])
local ttl = redis.call('TTL', KEYS[1])
if ttl < 0 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
    ttl = tonumber(ARGV[1])
end
return {count, ttl}
"""


async def consume_auth_attempt(key: str) -> tuple[int, int]:
    count, ttl = await _auth_execute("EVAL", _RATE_LIMIT, 1, key, 60)
    return int(count), int(ttl)
