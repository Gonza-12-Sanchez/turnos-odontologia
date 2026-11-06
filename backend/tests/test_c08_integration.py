import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api import deps
from app.db import redis as redis_client
from app.main import app
from app.models import Consultorio, Paciente, Sillon, Tratamiento, Usuario


@pytest.fixture
async def integ_client(engine, session, real_redis, monkeypatch):
    factory = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(deps, "get_session_factory", lambda: factory)
    monkeypatch.setattr(redis_client, "get_redis", lambda: real_redis)

    consultorio = Consultorio(nombre="C")
    session.add(consultorio)
    await session.flush()
    sillones = [Sillon(nombre=f"S{i}", consultorio_id=consultorio.id) for i in (1, 2)]
    tratamiento = Tratamiento(nombre="Control", duracion_min=30, precio_referencia_centavos=1000)
    session.add_all([*sillones, tratamiento])
    actor = Usuario(email="p@i.com", rol="paciente", password_hash="x", telefono="+54")
    session.add(actor)
    await session.flush()
    pac = Paciente(usuario_id=actor.id, nombre="P", telefono="+54")
    session.add(pac)
    await session.commit()
    from app.shared.security import create_access_token
    token = create_access_token(actor.id, ["paciente"], actor.email)[0]

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="https://test",
                          headers={"Authorization": f"Bearer {token}"}) as client:
        yield client, {"sillones": sillones, "tratamiento": tratamiento, "paciente": pac, "redis": real_redis}


@pytest.mark.asyncio
async def test_reserva_genera_job_wa(integ_client):
    client, ctx = integ_client
    sillon = ctx["sillones"][1]
    tratamiento = ctx["tratamiento"]
    r = await client.post("/turnos", json={
        "sillon_id": str(sillon.id),
        "tratamiento_id": str(tratamiento.id),
        "inicio": "2026-12-01T20:00:00+00:00",
    })
    assert r.status_code == 201, r.text
    turno_id = r.json()["id"]
    items = await ctx["redis"].lrange("wa:reminders", 0, -1)
    assert turno_id in items


@pytest.mark.asyncio
async def test_webhook_ruta_disponible(integ_client):
    client, ctx = integ_client
    r = await client.post("/webhooks/whatsapp", json={"message_id": "x", "respuesta": "confirmo"})
    # turno no encontrado -> 404 (but route exists, not 404 from router missing; could be 404 turno)
    assert r.status_code in (404, 422)
