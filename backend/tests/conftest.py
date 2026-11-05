"""Fixtures de test: AsyncClient (health) + engine/session sobre turnos_test."""

import os
import uuid

import pytest
import redis.asyncio as redis
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import app.models
from app.db.base import Base
from app.main import app  # re-importar app después del import de modelos

DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://turnos:turnos@localhost:5432/turnos_test"
)
if not DATABASE_URL.split("?", 1)[0].endswith("/turnos_test"):
    raise RuntimeError("Los tests solo pueden usar la base turnos_test")


class NamespacedRedis(redis.Redis):
    """Redis real con claves aisladas; también prefija las KEYS de Lua."""

    async def execute_command(self, *args, **options):
        command, *values = args
        name = str(command).upper()
        if name in {"GET", "SET", "INCR", "INCRBY", "EXPIRE", "PEXPIRE", "TTL", "PTTL", "EXISTS"}:
            values[0] = self.prefix + str(values[0])
        elif name == "DEL":
            values = [self.prefix + str(key) for key in values]
        elif name == "EVAL":
            for i in range(int(values[1])):
                values[2 + i] = self.prefix + str(values[2 + i])
        return await super().execute_command(command, *values, **options)


@pytest.fixture
async def real_redis():
    client = NamespacedRedis.from_url(
        os.environ.get("TEST_REDIS_URL", "redis://127.0.0.1:6379/15"),
        decode_responses=True,
        socket_timeout=2,
        socket_connect_timeout=2,
    )
    client.prefix = f"turnos-test:{uuid.uuid4()}:"
    await client.ping()
    try:
        yield client
    finally:
        async for key in client.scan_iter(match=client.prefix + "*"):
            await redis.Redis.execute_command(client, "DEL", key)
        await client.aclose()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def engine():
    eng = create_async_engine(DATABASE_URL, poolclass=NullPool)
    yield eng
    await eng.dispose()


@pytest.fixture
async def session(engine):
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as s:
        yield s
    # Limpieza entre tests: TRUNCATE CASCADE (más robusto que DELETE para datos commiteados).
    async with engine.begin() as conn:
        table_names = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
        if table_names:
            await conn.execute(text(f"TRUNCATE TABLE {table_names} CASCADE"))
