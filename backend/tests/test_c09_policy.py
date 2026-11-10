"""C-09: política de seña por tratamiento (tarea 2.1)."""

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api import deps
from app.db import redis as redis_client
from app.main import app
from app.models import Consultorio, Usuario
from app.shared.security import create_access_token


class _FakeRedis:
    """Redis doble que degrada gracefully sin servidor real."""

    async def get(self, *a, **k):
        return None

    async def set(self, *a, **k):
        return True

    async def lpush(self, *a, **k):
        return 0

    async def ping(self):
        return True

    async def scan_iter(self, *a, **k) -> AsyncIterator[str]:
        if False:  # pragma: no cover - async generator sin items
            yield ""

    async def execute_command(self, *a, **k):
        return None

    async def close(self):
        pass


@pytest.fixture
async def c09_client(engine, session, monkeypatch):
    """Cliente autenticado como secretaria con sesiones y Redis aislados."""
    monkeypatch.setattr(
        deps, "get_session_factory", lambda: async_sessionmaker(engine, expire_on_commit=False)
    )
    monkeypatch.setattr(redis_client, "get_redis", lambda: _FakeRedis())
    consultorio = Consultorio(nombre="Consultorio C09")
    session.add(consultorio)
    await session.flush()
    actor = Usuario(email="secre.c09@example.com", rol="secretaria", password_hash="ficticio")
    session.add(actor)
    await session.flush()
    token = create_access_token(actor.id, ["secretaria"], actor.email)[0]
    await session.commit()
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(
        transport=transport, base_url="https://test", headers={"Authorization": f"Bearer {token}"}
    ) as client:
        yield client, {"consultorio_id": str(consultorio.id)}


# --- RED: estos tests fallan hasta que la política de seña esté implementada ---

async def test_tratamiento_obligatoria_con_monto(c09_client):
    client, _ = c09_client
    response = await client.post(
        "/api/config/tratamientos",
        json={
            "nombre": "Limpieza con seña",
            "duracion_min": 30,
            "sena_politica": "obligatoria",
            "sena_centavos": 15000,
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["sena_politica"] == "obligatoria"
    assert data["sena_centavos"] == 15000


async def test_tratamiento_opcional_con_monto(c09_client):
    client, _ = c09_client
    response = await client.post(
        "/api/config/tratamientos",
        json={
            "nombre": "Control opcional",
            "duracion_min": 15,
            "sena_politica": "opcional",
            "sena_centavos": 8000,
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["sena_politica"] == "opcional"
    assert data["sena_centavos"] == 8000


async def test_tratamiento_deshabilitada_sin_monto(c09_client):
    client, _ = c09_client
    response = await client.post(
        "/api/config/tratamientos",
        json={
            "nombre": "Solo efectivo",
            "duracion_min": 20,
            "sena_politica": "deshabilitada",
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["sena_politica"] == "deshabilitada"
    assert data["sena_centavos"] is None


async def test_tratamiento_default_es_deshabilitada(c09_client):
    client, _ = c09_client
    response = await client.post(
        "/api/config/tratamientos",
        json={"nombre": "Default", "duracion_min": 10},
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["sena_politica"] == "deshabilitada"
    assert data["sena_centavos"] is None


async def test_tratamiento_obligatoria_sin_monto_rechazado(c09_client):
    client, _ = c09_client
    response = await client.post(
        "/api/config/tratamientos",
        json={
            "nombre": "Sin monto",
            "duracion_min": 10,
            "sena_politica": "obligatoria",
        },
    )
    assert response.status_code == 422, response.text


async def test_tratamiento_sena_float_rechazado(c09_client):
    client, _ = c09_client
    response = await client.post(
        "/api/config/tratamientos",
        json={
            "nombre": "Float",
            "duracion_min": 10,
            "sena_politica": "opcional",
            "sena_centavos": 10.5,
        },
    )
    assert response.status_code == 422, response.text


async def test_tratamiento_sena_negativo_rechazado(c09_client):
    client, _ = c09_client
    response = await client.post(
        "/api/config/tratamientos",
        json={
            "nombre": "Negativo",
            "duracion_min": 10,
            "sena_politica": "opcional",
            "sena_centavos": -100,
        },
    )
    assert response.status_code == 422, response.text


async def test_tratamiento_sena_booleano_rechazado(c09_client):
    client, _ = c09_client
    response = await client.post(
        "/api/config/tratamientos",
        json={
            "nombre": "Bool",
            "duracion_min": 10,
            "sena_politica": "opcional",
            "sena_centavos": True,
        },
    )
    assert response.status_code == 422, response.text


async def test_tratamiento_politica_invalida_rechazado(c09_client):
    client, _ = c09_client
    response = await client.post(
        "/api/config/tratamientos",
        json={
            "nombre": "Invalida",
            "duracion_min": 10,
            "sena_politica": "ninguna",
        },
    )
    assert response.status_code == 422, response.text


async def test_tratamiento_anonimo_401(engine, session, monkeypatch):
    monkeypatch.setattr(
        deps, "get_session_factory", lambda: async_sessionmaker(engine, expire_on_commit=False)
    )
    monkeypatch.setattr(redis_client, "get_redis", lambda: _FakeRedis())
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="https://test") as client:
        response = await client.post(
            "/api/config/tratamientos",
            json={"nombre": "Anon", "duracion_min": 10},
        )
        assert response.status_code == 401, response.text


async def test_tratamiento_paciente_403(c09_client, engine, session, monkeypatch):
    # Re-autenticar como paciente
    monkeypatch.setattr(
        deps, "get_session_factory", lambda: async_sessionmaker(engine, expire_on_commit=False)
    )
    monkeypatch.setattr(redis_client, "get_redis", lambda: _FakeRedis())
    paciente = Usuario(email="pac.c09@example.com", rol="paciente", password_hash="ficticio")
    session.add(paciente)
    await session.flush()
    token = create_access_token(paciente.id, ["paciente"], paciente.email)[0]
    await session.commit()
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(
        transport=transport, base_url="https://test", headers={"Authorization": f"Bearer {token}"}
    ) as client:
        response = await client.post(
            "/api/config/tratamientos",
            json={"nombre": "Pac", "duracion_min": 10},
        )
        assert response.status_code == 403, response.text
