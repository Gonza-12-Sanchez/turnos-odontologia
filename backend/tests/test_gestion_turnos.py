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
            pac = Paciente(
                usuario_id=actor.id, nombre="Paciente ficticio", telefono="+54 9 11 0000-0000"
            )
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
        yield (
            client,
            {
                "sillones": sillones,
                "tratamiento": tratamiento,
                "actors": actors,
                "turno": turno,
            },
        )


async def test_asistencia_proyectada_y_auditada(gestion_client):
    client, ctx = gestion_client
    turno = ctx["turno"]
    actor = ctx["actors"]["odontologo"]
    client.headers["Authorization"] = f"Bearer {actor['token']}"
    agenda = await client.get("/agenda", params={"fecha": turno.inicio.date().isoformat()})
    assert agenda.status_code == 200
    acciones = agenda.json()[0]["turnos"][0]["acciones"]
    assert acciones["asistencia"] is True
    assert acciones["confirmar"] is False
    assert acciones["cancelar"] is False

    base = f"/turnos/{turno.id}"
    response = await client.patch(
        f"{base}/marcar-asistencia",
        json={"estado": "asistido", "motivo": "Atención realizada", "origen": "mostrador"},
    )
    assert response.status_code == 200, response.text
    assert (await client.get(f"{base}/gestion")).json()["estado"] == "asistido"

    history = await client.get(f"{base}/historial")
    assert history.status_code == 200
    assert history.headers["cache-control"] == "no-store"
    (event,) = history.json()
    assert event["actor_id"] == str(actor["id"])
    assert event["origen"] == "mostrador"
    assert event["accion"] == "asistido"
    assert event["motivo"] == "Atención realizada"
    assert datetime.fromisoformat(event["fecha"]).tzinfo is not None

    client.headers["Authorization"] = f"Bearer {ctx['actors']['paciente']['token']}"
    assert (await client.get(f"{base}/historial")).status_code == 403


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
    alternativas = response.json()["alternativas"]
    assert alternativas
    assert all(datetime.fromisoformat(a["inicio"]) != start for a in alternativas)
    original = (await client.get(f"/turnos/{turno.id}/gestion")).json()
    assert datetime.fromisoformat(original["inicio"]) == turno.inicio
    assert original["sillon_id"] == str(turno.sillon_id)


@pytest.mark.parametrize("accion", ["cancelar", "reprogramar"])
@pytest.mark.parametrize("seconds,expected", [(7199, 422), (7200, 200)])
async def test_ventana_staff_y_conservacion_del_turno(
    gestion_client, monkeypatch, accion, seconds, expected
):
    from app.services import gestion_turnos_service as service

    client, ctx = gestion_client
    turno = ctx["turno"]
    original = turno.inicio
    frozen = original - timedelta(seconds=seconds)

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return frozen.astimezone(tz) if tz is not None else frozen.replace(tzinfo=None)

    monkeypatch.setattr(service, "datetime", FixedDatetime)
    monkeypatch.setattr(service.settings, "appointment_cancel_minutes", 120)
    path = f"/turnos/{turno.id}"
    destination = original + timedelta(hours=2)
    body = {"inicio": destination.isoformat(), "sillon_id": str(ctx["sillones"][1].id)}
    response = await client.patch(
        f"{path}/{accion}", json=body if accion == "reprogramar" else None
    )
    assert response.status_code == expected, response.text
    stored = (await client.get(f"{path}/gestion")).json()
    if expected == 422:
        assert "ventana" in response.json()["detail"]
        assert stored["estado"] == "reservado"
        assert datetime.fromisoformat(stored["inicio"]) == original
        assert stored["sillon_id"] == str(turno.sillon_id)
        assert (await client.get(f"{path}/historial")).json() == []
    elif accion == "cancelar":
        assert stored["estado"] == "cancelado"
        assert (await client.patch(f"{path}/cancelar")).status_code == 422
    else:
        assert datetime.fromisoformat(stored["inicio"]) == destination
        assert datetime.fromisoformat(stored["fin"]) == destination + timedelta(minutes=30)
        assert stored["sillon_id"] == str(ctx["sillones"][1].id)


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


@pytest.mark.parametrize(
    ("endpoint", "payload", "action"),
    [
        ("confirmar", None, "confirmar"),
        ("cancelar", None, "cancelar"),
        ("reprogramar", {"inicio": "2026-12-01T15:00:00Z"}, "reprogramar"),
        ("marcar-asistencia", {"estado": "ausente"}, "ausente"),
        ("sobreturno", {"motivo": "Urgencia"}, "sobreturno"),
        ("", {"origen": "mostrador"}, "cambiar_origen"),
    ],
)
async def test_transicion_staff_persiste_evento(gestion_client, endpoint, payload, action):
    client, ctx = gestion_client
    base = f"/turnos/{ctx['turno'].id}"
    response = await client.patch(f"{base}/{endpoint}" if endpoint else base, json=payload)
    assert response.status_code == 200, response.text

    history = await client.get(f"{base}/historial")
    assert history.status_code == 200
    (event,) = history.json()
    assert event["accion"] == action
    assert event["actor_id"] == str(ctx["actors"]["secretaria"]["id"])
    assert datetime.fromisoformat(event["fecha"]).utcoffset() is not None
    assert event["origen"] in {"online", "mostrador"}
