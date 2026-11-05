"""Contrato C-05: disponibilidad pública y reserva."""

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
async def turnos_client(engine, session, real_redis, monkeypatch):
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
            email=f"{role}.turnos@example.com",
            rol=role,
            password_hash="ficticio",
            telefono="+54 9 11 0000-0000",
        )
        session.add(actor)
        await session.flush()
        paciente_obj = None
        if role == "paciente":
            pac = Paciente(
                usuario_id=actor.id, nombre="Paciente ficticio", telefono="+54 9 11 0000-0000"
            )
            session.add(pac)
            await session.flush()
            paciente_obj = pac
        token = create_access_token(actor.id, [role], actor.email)[0]
        actors[role] = {"id": actor.id, "token": token, "paciente": paciente_obj}

    await session.commit()

    transport = ASGITransport(app=app, raise_app_exceptions=True)
    async with AsyncClient(
        transport=transport,
        base_url="https://test",
        headers={"Authorization": f"Bearer {actors['paciente']['token']}"},
    ) as client:
        yield (
            client,
            {
                "consultorio_id": str(consultorio.id),
                "sillones": sillones,
                "tratamiento": tratamiento,
                "actors": actors,
            },
        )


async def _seed_turno(session, context, *, sillon_index=0, start=None):
    if start is None:
        start = datetime(2026, 12, 1, 13, 0, tzinfo=UTC)
    sillones = context.get("sillones", None)
    # context may be the dict from turnos_client
    if sillones is None:
        # fallback: load from db not needed
        pass
    sil = context["sillones"][sillon_index]
    tratamiento = context["tratamiento"]
    paciente_id = context["actors"]["paciente"]["paciente"].id
    turno = Turno(
        paciente_id=paciente_id,
        sillon_id=sil.id,
        tratamiento_id=tratamiento.id,
        inicio=start,
        fin=start + timedelta(minutes=30),
        estado="reservado",
        origen="online",
    )
    session.add(turno)
    await session.commit()
    return turno, sil


@pytest.mark.asyncio
async def test_horarios_libres_excluye_ocupados(turnos_client, session):
    client, context = turnos_client
    turno, sillon = await _seed_turno(session, context)
    tratamiento = context["tratamiento"]
    response = await client.get(
        "/horarios-libres",
        params={"tratamiento": str(tratamiento.id), "fecha": "2026-12-01"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data) > 0
    occupied_start = turno.inicio.isoformat()
    for slot in data:
        if slot["sillon_id"] == str(sillon.id):
            assert slot["inicio"] != occupied_start


@pytest.mark.asyncio
async def test_horarios_libres_filtro_sillon(turnos_client):
    client, context = turnos_client
    tratamiento = context["tratamiento"]
    sillon = context["sillones"][0]
    response = await client.get(
        "/horarios-libres",
        params={
            "tratamiento": str(tratamiento.id),
            "fecha": "2026-12-01",
            "sillon": str(sillon.id),
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert all(slot["sillon_id"] == str(sillon.id) for slot in data)


@pytest.mark.asyncio
async def test_reserva_feliz_calcula_fin(turnos_client):
    client, context = turnos_client
    tratamiento = context["tratamiento"]
    sillon = context["sillones"][0]
    inicio = "2026-12-01T14:00:00+00:00"
    response = await client.post(
        "/turnos",
        json={
            "sillon_id": str(sillon.id),
            "tratamiento_id": str(tratamiento.id),
            "inicio": inicio,
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["fin"] == "2026-12-01T14:30:00Z"
    assert data["estado"] == "reservado"


@pytest.mark.asyncio
async def test_reserva_sin_login_401(turnos_client):
    client, context = turnos_client
    tratamiento = context["tratamiento"]
    sillon = context["sillones"][0]
    del client.headers["Authorization"]
    response = await client.post(
        "/turnos",
        json={
            "sillon_id": str(sillon.id),
            "tratamiento_id": str(tratamiento.id),
            "inicio": "2026-12-01T15:00:00+00:00",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_reserva_rol_no_paciente_403(turnos_client):
    client, context = turnos_client
    tratamiento = context["tratamiento"]
    sillon = context["sillones"][0]
    client.headers["Authorization"] = f"Bearer {context['actors']['odontologo']['token']}"
    response = await client.post(
        "/turnos",
        json={
            "sillon_id": str(sillon.id),
            "tratamiento_id": str(tratamiento.id),
            "inicio": "2026-12-01T15:30:00+00:00",
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_slot_ocupado_409_con_alternativas(turnos_client, session):
    client, context = turnos_client
    _turno, sillon = await _seed_turno(
        session, context, start=datetime(2026, 12, 1, 16, 0, tzinfo=UTC)
    )
    tratamiento = context["tratamiento"]
    response = await client.post(
        "/turnos",
        json={
            "sillon_id": str(sillon.id),
            "tratamiento_id": str(tratamiento.id),
            "inicio": "2026-12-01T16:00:00+00:00",
        },
    )
    assert response.status_code == 409, response.text
    data = response.json()
    assert "alternativas" in data
    assert isinstance(data["alternativas"], list)


@pytest.mark.asyncio
async def test_naive_422(turnos_client):
    client, context = turnos_client
    tratamiento = context["tratamiento"]
    sillon = context["sillones"][0]
    response = await client.post(
        "/turnos",
        json={
            "sillon_id": str(sillon.id),
            "tratamiento_id": str(tratamiento.id),
            "inicio": "2026-12-01T17:00:00",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_concurrencia(turnos_client):
    client, context = turnos_client
    tratamiento = context["tratamiento"]
    sillon = context["sillones"][0]
    payload = {
        "sillon_id": str(sillon.id),
        "tratamiento_id": str(tratamiento.id),
        "inicio": "2026-12-01T18:00:00+00:00",
    }
    import asyncio

    responses = await asyncio.gather(
        client.post("/turnos", json=payload),
        client.post("/turnos", json=payload),
    )
    statuses = sorted(r.status_code for r in responses)
    assert statuses == [201, 409], statuses


@pytest.mark.asyncio
async def test_cache_hit_e_invalidacion(turnos_client):
    client, context = turnos_client
    tratamiento = context["tratamiento"]
    sillon = context["sillones"][0]
    # first call
    r1 = await client.get(
        "/horarios-libres",
        params={
            "tratamiento": str(tratamiento.id),
            "fecha": "2026-12-01",
            "sillon": str(sillon.id),
        },
    )
    assert r1.status_code == 200
    # reserve a slot
    slot_inicio = r1.json()[0]["inicio"] if r1.json() else "2026-12-01T19:00:00+00:00"
    await client.post(
        "/turnos",
        json={
            "sillon_id": str(sillon.id),
            "tratamiento_id": str(tratamiento.id),
            "inicio": slot_inicio,
        },
    )
    # after reservation, the slot should be gone
    r2 = await client.get(
        "/horarios-libres",
        params={
            "tratamiento": str(tratamiento.id),
            "fecha": "2026-12-01",
            "sillon": str(sillon.id),
        },
    )
    assert r2.status_code == 200
    starts = [s["inicio"] for s in r2.json()]
    assert slot_inicio not in starts


@pytest.mark.asyncio
async def test_enqueue_recordatorio(turnos_client, real_redis):
    client, context = turnos_client
    tratamiento = context["tratamiento"]
    sillon = context["sillones"][1]
    response = await client.post(
        "/turnos",
        json={
            "sillon_id": str(sillon.id),
            "tratamiento_id": str(tratamiento.id),
            "inicio": "2026-12-01T20:00:00+00:00",
        },
    )
    assert response.status_code == 201, response.text
    turno_id = response.json()["id"]
    # lpush key not namespaced by NamespacedRedis
    items = await real_redis.lrange("wa:reminders", 0, -1)
    assert turno_id in items
