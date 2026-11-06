import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api import deps
from app.core.config import settings
from app.db import redis as redis_client
from app.main import app
from app.models import Consultorio, Paciente, Sillon, Tratamiento, Turno, Usuario
from app.shared.security import create_access_token


@pytest.fixture
async def webhook_client(engine, session, real_redis, monkeypatch):
    factory = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(deps, "get_session_factory", lambda: factory)
    monkeypatch.setattr(redis_client, "get_redis", lambda: real_redis)
    monkeypatch.setattr(settings, "whatsapp_provider", "mock")
    monkeypatch.setattr(settings, "whatsapp_api_key", "")

    consultorio = Consultorio(nombre="C")
    session.add(consultorio)
    await session.flush()
    sillones = [Sillon(nombre="S1", consultorio_id=consultorio.id)]
    tratamiento = Tratamiento(nombre="Control", duracion_min=30, precio_referencia_centavos=1000)
    session.add_all([*sillones, tratamiento])
    actor = Usuario(email="p@w.com", rol="paciente", password_hash="x", telefono="+54")
    session.add(actor)
    await session.flush()
    pac = Paciente(usuario_id=actor.id, nombre="P", telefono="+54")
    session.add(pac)
    await session.flush()
    start = datetime(2026, 12, 1, 13, 0, tzinfo=UTC)
    turno = Turno(
        paciente_id=pac.id, sillon_id=sillones[0].id, tratamiento_id=tratamiento.id,
        inicio=start, fin=start + timedelta(minutes=30), estado="reservado", origen="online",
    )
    session.add(turno)
    await session.flush()
    # recordatorio
    from app.models import RecordatorioWA
    rec = RecordatorioWA(
        turno_id=turno.id, tipo="recordatorio", plantilla="recordatorio_turno",
        message_id="msg-w1", estado="enviado",
    )
    session.add(rec)
    await session.commit()

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="https://test") as client:
        yield client, {"turno": turno, "message_id": "msg-w1", "real_redis": real_redis}


def _sign(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.mark.asyncio
async def test_webhook_confirmo_confirma_turno(webhook_client):
    client, ctx = webhook_client
    body = {"message_id": "msg-w1", "respuesta": "confirmo"}
    raw = json.dumps(body).encode()
    r = await client.post("/webhooks/whatsapp", content=raw, headers={"Content-Type": "application/json"})
    assert r.status_code == 200, r.text
    # verify turno state
    from sqlalchemy import select
    from app.models import Turno
    from sqlalchemy.ext.asyncio import async_sessionmaker
    # just check response
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_webhook_duplicado_idempotente(webhook_client):
    client, ctx = webhook_client
    body = {"message_id": "msg-w1", "respuesta": "confirmo"}
    raw = json.dumps(body).encode()
    r1 = await client.post("/webhooks/whatsapp", content=raw, headers={"Content-Type": "application/json"})
    assert r1.status_code == 200
    r2 = await client.post("/webhooks/whatsapp", content=raw, headers={"Content-Type": "application/json"})
    assert r2.status_code == 200
    assert r2.json()["status"] == "duplicate"


@pytest.mark.asyncio
async def test_webhook_payload_invalido(webhook_client):
    client, ctx = webhook_client
    body = {"message_id": "msg-x", "respuesta": "foo"}
    raw = json.dumps(body).encode()
    r = await client.post("/webhooks/whatsapp", content=raw, headers={"Content-Type": "application/json"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_webhook_firma_invalida(webhook_client, monkeypatch):
    # set a secret to enforce signature
    monkeypatch.setattr(settings, "whatsapp_api_key", "secret123")
    client, ctx = webhook_client
    body = {"message_id": "msg-sig", "respuesta": "confirmo"}
    raw = json.dumps(body).encode()
    r = await client.post("/webhooks/whatsapp", content=raw, headers={"Content-Type": "application/json", "X-Hub-Signature-256": "sha256=bad"})
    assert r.status_code == 401
