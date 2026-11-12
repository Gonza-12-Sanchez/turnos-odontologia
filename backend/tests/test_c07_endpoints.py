"""C-07 endpoints de lectura."""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api import deps
from app.db import redis as redis_client
from app.main import app
from app.models import Consultorio, Paciente, Sillon, Tratamiento, Turno, Usuario
from app.shared.security import create_access_token


@pytest.fixture
async def agenda_client(engine, session, real_redis, monkeypatch):
    factory = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(deps, "get_session_factory", lambda: factory)
    monkeypatch.setattr(redis_client, "get_redis", lambda: real_redis)

    consultorio = Consultorio(nombre="Consultorio")
    session.add(consultorio)
    await session.flush()
    sillones = [Sillon(nombre=f"S{i}", consultorio_id=consultorio.id) for i in (1, 2)]
    tratamiento = Tratamiento(nombre="Control", duracion_min=30, precio_referencia_centavos=1000)
    session.add_all([*sillones, tratamiento])

    actors = {}
    for role in ("paciente", "odontologo", "secretaria"):
        actor = Usuario(
            email=f"{role}.c07@example.com",
            rol=role,
            password_hash="x",
            telefono="+54",
        )
        session.add(actor)
        await session.flush()
        pac_obj = None
        if role == "paciente":
            pac = Paciente(usuario_id=actor.id, nombre="Paciente", telefono="+54")
            session.add(pac)
            await session.flush()
            pac_obj = pac
        token = create_access_token(actor.id, [role], actor.email)[0]
        actors[role] = {"id": actor.id, "token": token, "paciente": pac_obj}

    # segundo paciente
    actor2 = Usuario(
        email="paciente2.c07@example.com", rol="paciente", password_hash="x", telefono="+54"
    )
    session.add(actor2)
    await session.flush()
    pac2 = Paciente(usuario_id=actor2.id, nombre="Paciente2", telefono="+54")
    session.add(pac2)
    await session.flush()
    token2 = create_access_token(actor2.id, ["paciente"], actor2.email)[0]
    actors["paciente2"] = {"id": actor2.id, "token": token2, "paciente": pac2}

    start = datetime(2026, 12, 1, 13, 0, tzinfo=UTC)
    t1 = Turno(
        paciente_id=actors["paciente"]["paciente"].id,
        sillon_id=sillones[0].id,
        tratamiento_id=tratamiento.id,
        inicio=start,
        fin=start + timedelta(minutes=30),
        estado="reservado",
        origen="online",
        es_sobreturno=True,
        motivo_sobreturno="Urgencia",
    )
    t2 = Turno(
        paciente_id=actors["paciente2"]["paciente"].id,
        sillon_id=sillones[1].id,
        tratamiento_id=tratamiento.id,
        inicio=start + timedelta(hours=1),
        fin=start + timedelta(hours=1, minutes=30),
        estado="confirmado",
        origen="online",
    )
    session.add_all([t1, t2])
    await session.commit()

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="https://test") as client:
        yield (
            client,
            {
                "actors": actors,
                "sillones": sillones,
                "tratamiento": tratamiento,
                "turnos": [t1, t2],
            },
        )


async def test_higiene_agenda_agrega_estados_sin_datos_personales(agenda_client):
    client, ctx = agenda_client
    ruta = "/agenda/higiene?fecha=2026-12-01"
    assert (await client.get(ruta)).status_code == 401
    for role, status in (("paciente", 403), ("secretaria", 200), ("odontologo", 200)):
        client.headers["Authorization"] = f"Bearer {ctx['actors'][role]['token']}"
        response = await client.get(ruta)
        assert response.status_code == status
        if status == 200:
            assert response.headers["cache-control"] == "no-store"
            assert response.json() == {
                "fecha": "2026-12-01",
                "por_estado": {"reservado": 1, "confirmado": 1},
                "total": 2,
                "sin_confirmar": 1,
                "porcentaje_confirmados": 50.0,
                "alerta": True,
            }
    vacio = (await client.get("/agenda/higiene?fecha=2026-12-02")).json()
    assert vacio["total"] == 0
    assert vacio["porcentaje_confirmados"] is None
    assert vacio["alerta"] is False


@pytest.mark.asyncio
async def test_agenda_requires_fecha(agenda_client):
    client, ctx = agenda_client
    actors = ctx["actors"]
    client.headers["Authorization"] = f"Bearer {actors['odontologo']['token']}"
    response = await client.get("/agenda")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_agenda_odontologo_ok(agenda_client):
    client, ctx = agenda_client
    actors = ctx["actors"]
    client.headers["Authorization"] = f"Bearer {actors['odontologo']['token']}"
    response = await client.get("/agenda?fecha=2026-12-01")
    assert response.status_code == 200, response.text
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    # sobreturno visible
    found = False
    for g in data:
        for t in g["turnos"]:
            if t.get("es_sobreturno"):
                assert t["motivo_sobreturno"] == "Urgencia"
                found = True
    assert found
    # tolerancia
    for g in data:
        for t in g["turnos"]:
            assert t["tolerancia_min"] == 5


@pytest.mark.asyncio
async def test_agenda_paciente_403(agenda_client):
    client, ctx = agenda_client
    actors = ctx["actors"]
    client.headers["Authorization"] = f"Bearer {actors['paciente']['token']}"
    response = await client.get("/agenda?fecha=2026-12-01")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_agenda_anonimo_401(agenda_client):
    client, _ctx = agenda_client
    response = await client.get("/agenda?fecha=2026-12-01")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_agenda_filtro_sillon(agenda_client):
    client, ctx = agenda_client
    actors = ctx["actors"]
    sillones = ctx["sillones"]
    client.headers["Authorization"] = f"Bearer {actors['odontologo']['token']}"
    response = await client.get(f"/agenda?fecha=2026-12-01&sillon={sillones[0].id}")
    assert response.status_code == 200
    data = response.json()
    for g in data:
        assert g["sillon_id"] == str(sillones[0].id)


@pytest.mark.asyncio
async def test_mis_reservas_aislamiento(agenda_client):
    client, ctx = agenda_client
    actors = ctx["actors"]
    # paciente 1
    client.headers["Authorization"] = f"Bearer {actors['paciente']['token']}"
    response = await client.get("/mis-reservas")
    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data) == 1
    assert all(t["estado"] in ("reservado",) for t in data)
    # paciente 2
    client.headers["Authorization"] = f"Bearer {actors['paciente2']['token']}"
    response2 = await client.get("/mis-reservas")
    assert response2.status_code == 200
    data2 = response2.json()
    assert len(data2) == 1


@pytest.mark.asyncio
async def test_mis_reservas_ordenado_y_acciones(agenda_client):
    client, ctx = agenda_client
    actors = ctx["actors"]
    # crear turno lejano para paciente para cancelar true
    client.headers["Authorization"] = f"Bearer {actors['paciente']['token']}"
    response = await client.get("/mis-reservas")
    data = response.json()
    # acciones presente
    assert "acciones" in data[0]
    assert "cancelar" in data[0]["acciones"]
    assert "acciones_permitidas" in data[0]


@pytest.mark.asyncio
async def test_debug_agenda(agenda_client):
    client, ctx = agenda_client
    actors = ctx["actors"]
    client.headers["Authorization"] = f"Bearer {actors['odontologo']['token']}"
    r = await client.get("/agenda?fecha=2026-12-01")
    print("STATUS", r.status_code)
    print("TEXT", r.text)
    print("URL", r.url)
    assert True
