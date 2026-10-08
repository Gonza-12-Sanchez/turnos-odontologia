"""Smoke del contrato specs/platform/health/spec.md (4 escenarios)."""

import asyncio
import time

from app.api import health
from app.shared import settings as settings_module


async def _up() -> str:
    return "up"


async def _down() -> str:
    raise ConnectionError("redis caído (simulado)")


async def _slow() -> str:
    await asyncio.sleep(30)
    return "up"


async def test_happy_todo_levantado(client, monkeypatch):
    """Dado DB+Redis ok, GET /api/health → 200 ok con ambos up."""
    monkeypatch.setattr(health.db_engine, "check_db", _up)
    monkeypatch.setattr(health.redis_client, "check_redis", _up)
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"db": "up", "redis": "up"}}


async def test_error_redis_caido_degrada(client, monkeypatch):
    """Dado Redis caído, GET /api/health → 200 degraded (nunca 500)."""
    monkeypatch.setattr(health.db_engine, "check_db", _up)
    monkeypatch.setattr(health.redis_client, "check_redis", _down)
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "degraded", "checks": {"db": "up", "redis": "down"}}


async def test_borde_check_lento_acotado_por_timeout(client, monkeypatch):
    """Dado un check lento, se declara down y la respuesta queda acotada."""
    monkeypatch.setattr(settings_module.settings, "health_check_timeout_seconds", 0.2)
    monkeypatch.setattr(health.db_engine, "check_db", _slow)
    monkeypatch.setattr(health.redis_client, "check_redis", _up)
    start = time.perf_counter()
    response = await client.get("/api/health")
    elapsed = time.perf_counter() - start
    assert response.status_code == 200
    assert response.json()["checks"]["db"] == "down"
    assert elapsed < 10


async def test_acceso_anonimo_sin_token(client, monkeypatch):
    """Sin JWT, GET /api/health → 200 (endpoint público)."""
    monkeypatch.setattr(health.db_engine, "check_db", _up)
    monkeypatch.setattr(health.redis_client, "check_redis", _up)
    response = await client.get("/api/health")
    assert response.status_code == 200
