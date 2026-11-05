"""Contrato C-06: gestión del ciclo de vida del turno."""

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
async def gestion_client(engine, session, real_redis, monkeypatch):
    factory = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(deps, "get_session_factory", lambda: factory)
    monkeypatch.setattr(redis_client, "get_redis", lambda: real_redis)

    consultorio = Consultorio(nombre="Consultorio ficticio")
    session.add(consultorio)
    await session.flush()

    sillones = [Sillon(nombre=f"Sillón {i}", consultorio_id=consultorio.id) for i in (1, 2)]
    tratamiento = Tratamiento(nombre="Control", duracion_min=30, precio_referencia_centavos=1000)
    session.add_all([*sillones, tratamiento])

    actors = {}
    for role in ("paciente", "odontologo", "secretaria"):
        actor = Usuario(
            email=f"{role}.gestion@example.com",
            rol=role,
            password_hash="ficticio",
            telefono="+54 9 11 0000-0000",
        )
        session.add(actor)
        await session.flush()
        pac_obj = None
        if role == "paciente":
            pac = Paciente(usuario_id=actor.id, nombre="Paciente ficticio", telefono="+54 9 11 0000-0000")
            session.add(pac)
            await session.flush()
            pac_obj = pac
        token = create_access_token(actor.id, [role], actor.email)[0]
        actors[role] = {"id": actor.id, "token": token, "paciente": pac_obj}

    # turno base reservado en el futuro
    start = datetime(2026, 12, 1, 13, 0, tzinfo=UTC)
    turno = Turno(
        paciente_id=actors["paciente"]["paciente"].id,
        sillon_id=sillones[0].id,
        tratamiento_id=tratamiento.id,
        inicio=start,
        fin=start + timedelta(minutes=30),
        estado="reservado",
        origen="online",
    )
    session.add(turno)
    await session.commit()

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(
        transport=transport,
        base_url="https://test",
        headers={"Authorization": f"Bearer {actors['secretaria']['token']}"},
    ) as client:
        yield client, {
            "sillones": sillones,
            "tratamiento": tratamiento,
            "actors": actors,
            "turno": turno,
        }


@pytest.mark.asyncio
async def test_confirmar_turno(gestion_client):
    client, ctx = gestion_client
    turno = ctx["turno"]
    response = await client.patch(f"/turnos/{turno.id}/confirmar")
    assert response.status_code == 200, response.text
    assert response.json()["estado"] == "confirmado"
    assert response.json()["tolerancia_min"] == 5


@pytest.mark.asyncio
async def test_cancelar_ok(gestion_client):
    client, ctx = gestion_client
    turno = ctx["turno"]
    response = await client.patch(f"/turnos/{turno.id}/cancelar")
    assert response.status_code == 200, response.text
    assert response.json()["estado"] == "cancelado"


@pytest.mark.asyncio
async def test_cancelar_menos_2h_422(gestion_client, session):
    client, ctx = gestion_client
    actors = ctx["actors"]
    sillones = ctx["sillones"]
    tratamiento = ctx["tratamiento"]
    start = datetime.now(UTC) + timedelta(minutes=30)
    turno = Turno(
        paciente_id=actors["paciente"]["paciente"].id,
        sillon_id=sillones[0].id,
        tratamiento_id=tratamiento.id,
        inicio=start,
        fin=start + timedelta(minutes=30),
        estado="reservado",
        origen="online",
    )
    session.add(turno)
    await session.commit()
    # usar token de secretaria
    client.headers["Authorization"] = f"Bearer {actors['secretaria']['token']}"
    response = await client.patch(f"/turnos/{turno.id}/cancelar")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_reprogramar_feliz(gestion_client):
    client, ctx = gestion_client
    turno = ctx["turno"]
    sillones = ctx["sillones"]
    # reprogramar a otro sillón y hora libre
    response = await client.patch(
        f"/turnos/{turno.id}/reprogramar",
        json={
            "inicio": "2026-12-01T15:00:00+00:00",
            "sillon_id": str(sillones[1].id),
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["inicio"] == "2026-12-01T15:00:00Z"
    assert data["sillon_id"] == str(sillones[1].id)


@pytest.mark.asyncio
async def test_reprogramar_conflicto(gestion_client, session):
    client, ctx = gestion_client
    turno = ctx["turno"]
    sillones = ctx["sillones"]
    tratamiento = ctx["tratamiento"]
    actors = ctx["actors"]
    # ocupar el hueco destino
    start = datetime(2026, 12, 1, 16, 0, tzinfo=UTC)
    other = Turno(
        paciente_id=actors["paciente"]["paciente"].id,
        sillon_id=sillones[0].id,
        tratamiento_id=tratamiento.id,
        inicio=start,
        fin=start + timedelta(minutes=30),
        estado="reservado",
        origen="online",
    )
    session.add(other)
    await session.commit()
    response = await client.patch(
        f"/turnos/{turno.id}/reprogramar",
        json={"inicio": "2026-12-01T16:00:00+00:00"},
    )
    assert response.status_code == 409, response.text
    assert "alternativas" in response.json()


@pytest.mark.asyncio
async def test_sobreturno_secretaria_ok(gestion_client):
    client, ctx = gestion_client
    turno = ctx["turno"]
    response = await client.patch(
        f"/turnos/{turno.id}/sobreturno",
        json={"motivo": "Urgencia"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["es_sobreturno"] is True
    assert data["motivo_sobreturno"] == "Urgencia"


@pytest.mark.asyncio
async def test_sobreturno_paciente_403(gestion_client):
    client, ctx = gestion_client
    turno = ctx["turno"]
    actors = ctx["actors"]
    client.headers["Authorization"] = f"Bearer {actors['paciente']['token']}"
    response = await client.patch(
        f"/turnos/{turno.id}/sobreturno",
        json={"motivo": "Urgencia"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_marcar_asistencia_ok(gestion_client):
    client, ctx = gestion_client
    turno = ctx["turno"]
    # primero confirmar
    await client.patch(f"/turnos/{turno.id}/confirmar")
    response = await client.patch(
        f"/turnos/{turno.id}/marcar-asistencia",
        json={"estado": "asistido"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["estado"] == "asistido"


@pytest.mark.asyncio
async def test_marcar_asistencia_paciente_403(gestion_client):
    client, ctx = gestion_client
    turno = ctx["turno"]
    actors = ctx["actors"]
    client.headers["Authorization"] = f"Bearer {actors['paciente']['token']}"
    response = await client.patch(
        f"/turnos/{turno.id}/marcar-asistencia",
        json={"estado": "asistido"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_patch_turno_sobreturno(gestion_client):
    client, ctx = gestion_client
    turno = ctx["turno"]
    response = await client.patch(
        f"/turnos/{turno.id}",
        json={"es_sobreturno": True, "motivo_sobreturno": "Otro motivo"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["es_sobreturno"] is True