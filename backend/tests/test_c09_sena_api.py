"""C-09: POST /pagos/sena y GET /pagos/sena/{id} (tareas 4.2, 4.4)."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api import deps
from app.core.config import settings
from app.db import redis as redis_client
from app.main import app
from app.models import (
    Consultorio,
    Paciente,
    Sillon,
    Tratamiento,
    Turno,
    Usuario,
)
from app.services.mp_adapter import MPAdapter
from app.shared.security import create_access_token


class _FakeRedis:
    async def get(self, *a, **k):
        return None

    async def set(self, *a, **k):
        return True

    async def lpush(self, *a, **k):
        return 0

    async def ping(self):
        return True

    async def scan_iter(self, *a, **k):
        if False:
            yield ""

    async def execute_command(self, *a, **k):
        return None

    async def close(self):
        pass


class _MockMPAdapter(MPAdapter):
    async def crear_preferencia(
        self, access_token, external_reference, monto_centavos, notification_url, back_urls
    ):
        return {
            "id": f"pref_{external_reference}",
            "init_point": "https://mock.mp/checkout/pref_" + external_reference,
        }


@pytest.fixture
async def c09_sena_client(engine, session, monkeypatch):
    monkeypatch.setattr(
        deps, "get_session_factory", lambda: async_sessionmaker(engine, expire_on_commit=False)
    )
    monkeypatch.setattr(redis_client, "get_redis", lambda: _FakeRedis())
    consultorio = Consultorio(nombre="Consultorio Sena")
    session.add(consultorio)
    await session.flush()
    sillon = Sillon(consultorio_id=consultorio.id, nombre="Sillon Sena", is_active=True)
    session.add(sillon)
    tratamiento = Tratamiento(
        nombre="Limpieza",
        duracion_min=30,
        precio_referencia_centavos=10000,
        sena_politica="obligatoria",
        sena_centavos=3000,
    )
    session.add(tratamiento)
    await session.flush()
    paciente_user = Usuario(email="pac.sena@example.com", rol="paciente", password_hash="ficticio")
    session.add(paciente_user)
    await session.flush()
    paciente = Paciente(usuario_id=paciente_user.id, nombre="Paciente Sena", telefono="1112345678")
    session.add(paciente)
    await session.flush()
    token = create_access_token(paciente_user.id, ["paciente"], paciente_user.email)[0]
    # Inicio alineado a la grilla de 30 min (10:00 UTC)
    inicio = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)
    settings.mp_mode = "mock"
    await session.commit()
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(
        transport=transport,
        base_url="https://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as client:
        yield (
            client,
            {
                "sillon_id": str(sillon.id),
                "tratamiento_id": str(tratamiento.id),
                "inicio": inicio.isoformat(),
                "paciente_id": str(paciente.id),
                "usuario_id": str(paciente_user.id),
            },
        )


async def _post_sena(client, sillon_id, tratamiento_id, inicio, idem=None, token=None):
    headers = {}
    if idem:
        headers["Idempotency-Key"] = idem
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return await client.post(
        "/pagos/sena",
        json={"sillon_id": sillon_id, "tratamiento_id": tratamiento_id, "inicio": inicio},
        headers=headers,
    )


# --- RED: endpoint /pagos/sena no existe ---


async def test_pagos_sena_crea_checkout(c09_sena_client, monkeypatch):
    client, ctx = c09_sena_client
    from app.services.sena_service import SenaService

    mock_adapter = _MockMPAdapter()
    monkeypatch.setattr(
        SenaService, "mp_adapter", property(lambda self: mock_adapter), raising=False
    )
    response = await _post_sena(
        client, ctx["sillon_id"], ctx["tratamiento_id"], ctx["inicio"], idem=str(uuid4())
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["provider"] == "mercadopago"
    assert data["status"] == "pendiente"
    assert data["intento_id"] is not None
    assert data["checkout_url"] is not None
    assert data["monto_centavos"] == 3000
    assert data["moneda"] == "ARS"
    assert data["modo"] == "mock"


async def test_pagos_sena_replay_misma_clave(c09_sena_client, monkeypatch):
    client, ctx = c09_sena_client
    from app.services.sena_service import SenaService

    mock_adapter = _MockMPAdapter()
    monkeypatch.setattr(
        SenaService, "mp_adapter", property(lambda self: mock_adapter), raising=False
    )
    clave = str(uuid4())
    r1 = await _post_sena(
        client, ctx["sillon_id"], ctx["tratamiento_id"], ctx["inicio"], idem=clave
    )
    assert r1.status_code == 201, r1.text
    r2 = await _post_sena(
        client, ctx["sillon_id"], ctx["tratamiento_id"], ctx["inicio"], idem=clave
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["intento_id"] == r1.json()["intento_id"]


async def test_pagos_sena_clave_distinta_payload(c09_sena_client, monkeypatch):
    client, ctx = c09_sena_client
    from app.services.sena_service import SenaService

    mock_adapter = _MockMPAdapter()
    monkeypatch.setattr(
        SenaService, "mp_adapter", property(lambda self: mock_adapter), raising=False
    )
    clave = str(uuid4())
    r1 = await _post_sena(
        client, ctx["sillon_id"], ctx["tratamiento_id"], ctx["inicio"], idem=clave
    )
    assert r1.status_code == 201, r1.text
    inicio2 = datetime(2026, 11, 12, 11, 0, tzinfo=UTC).isoformat()
    r2 = await _post_sena(client, ctx["sillon_id"], ctx["tratamiento_id"], inicio2, idem=clave)
    assert r2.status_code == 409, r2.text


async def test_pagos_sena_sin_idempotency_key(c09_sena_client):
    client, ctx = c09_sena_client
    response = await _post_sena(client, ctx["sillon_id"], ctx["tratamiento_id"], ctx["inicio"])
    assert response.status_code == 422, response.text


async def test_pagos_sena_hueco_ocupado(c09_sena_client, session):
    client, ctx = c09_sena_client
    # Crear un turno que ocupe el hueco (mismo inicio del fixture)
    inicio = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)
    turno = Turno(
        paciente_id=ctx["paciente_id"],
        sillon_id=ctx["sillon_id"],
        tratamiento_id=ctx["tratamiento_id"],
        inicio=inicio,
        fin=inicio + timedelta(minutes=30),
        estado="reservado",
        origen="online",
    )
    session.add(turno)
    await session.commit()
    response = await _post_sena(
        client, ctx["sillon_id"], ctx["tratamiento_id"], inicio.isoformat(), idem=str(uuid4())
    )
    assert response.status_code == 409, response.text


async def test_pagos_sena_anonimo_401(engine, session, monkeypatch):
    monkeypatch.setattr(
        deps, "get_session_factory", lambda: async_sessionmaker(engine, expire_on_commit=False)
    )
    monkeypatch.setattr(redis_client, "get_redis", lambda: _FakeRedis())
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="https://test") as client:
        response = await _post_sena(client, str(uuid4()), str(uuid4()), "2026-12-01T10:00:00-03:00")
        assert response.status_code == 401, response.text


async def test_pagos_sena_tratamiento_sin_sena_422(c09_sena_client, session, monkeypatch):
    client, ctx = c09_sena_client
    # Tratamiento con sena deshabilitada -> 422 si se intenta pagar
    t2 = Tratamiento(
        nombre="Sin seña",
        duracion_min=15,
        precio_referencia_centavos=5000,
        sena_politica="deshabilitada",
        sena_centavos=None,
    )
    session.add(t2)
    await session.commit()
    response = await _post_sena(
        client, ctx["sillon_id"], str(t2.id), ctx["inicio"], idem=str(uuid4())
    )
    assert response.status_code == 422, response.text
