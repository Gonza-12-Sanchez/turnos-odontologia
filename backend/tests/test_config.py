"""Contrato C-04: persistencia auditada y API de configuración por rol."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api import deps
from app.db import redis as redis_client
from app.main import app
from app.models import ConfigAudit, Consultorio, Paciente, Sillon, Tratamiento, Turno, Usuario
from app.shared.security import create_access_token


@pytest.fixture
async def config_client(engine, session, real_redis, monkeypatch):
    factory = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(deps, "get_session_factory", lambda: factory)
    monkeypatch.setattr(redis_client, "get_redis", lambda: real_redis)
    consultorio = Consultorio(nombre="Consultorio ficticio")
    session.add(consultorio)
    actors = {}
    for role in ("secretaria", "odontologo", "paciente"):
        actor = Usuario(email=f"{role}.config@example.com", rol=role, password_hash="ficticio")
        session.add(actor)
        await session.flush()
        token = create_access_token(actor.id, [role], actor.email)[0]
        actors[role] = {"id": actor.id, "token": token}
    await session.commit()
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(
        transport=transport,
        base_url="https://test",
        headers={
            "Authorization": f"Bearer {actors['secretaria']['token']}",
        },
    ) as client:
        yield client, {"consultorio_id": str(consultorio.id), "actors": actors}


async def test_crud_sillon(config_client):
    client, context = config_client
    response = await client.post(
        "/api/config/sillones",
        json={
            "consultorio_id": context["consultorio_id"],
            "nombre": "  Sillón demo  ",
        },
    )
    assert response.status_code == 201, response.text
    sillon = response.json()
    assert sillon["nombre"] == "Sillón demo"
    assert sillon["activo"] is True
    url = "/api/config/sillones/" + sillon["id"]
    assert (await client.get(url)).json()["id"] == sillon["id"]
    updated = await client.patch(url, json={"nombre": "Sillón actualizado"})
    assert updated.status_code == 200
    assert updated.json()["consultorio_id"] == context["consultorio_id"]
    assert (await client.get("/api/config/sillones")).json() == {
        "items": [updated.json()],
        "total": 1,
        "page": 1,
        "page_size": 20,
    }
    assert (await client.delete(url)).status_code == 204
    assert (await client.get(url)).json()["activo"] is False
    assert (await client.get(url)).json()["deleted_at"] is not None
    assert (await client.get("/api/config/sillones")).json()["total"] == 0
    assert (await client.get("/api/config/sillones?activo=false")).json()["total"] == 1
    assert (await client.delete(url)).status_code == 204
    restored = await client.patch(url, json={"activo": True})
    assert restored.status_code == 200
    assert restored.json()["deleted_at"] is None


@pytest.mark.parametrize("role,expected", [(None, 401), ("paciente", 403), ("odontologo", 403)])
@pytest.mark.parametrize("resource", ["sillones", "tratamientos", "bloqueos"])
@pytest.mark.parametrize(
    "method,suffix",
    [
        ("GET", ""),
        ("POST", ""),
        ("GET", "/id"),
        ("PATCH", "/id"),
        ("DELETE", "/id"),
    ],
)
async def test_catalogo_rbac_todas_operaciones(
    config_client, resource, role, expected, method, suffix
):
    client, context = config_client
    if role is None:
        del client.headers["Authorization"]
    else:
        client.headers["Authorization"] = f"Bearer {context['actors'][role]['token']}"
    suffix = suffix.replace("id", str(uuid4()))
    response = await client.request(
        method, "/api/config/" + resource + suffix, json={} if method in {"POST", "PATCH"} else None
    )
    assert response.status_code == expected


async def test_crud_tratamiento(config_client):
    client, _ = config_client
    response = await client.post(
        "/api/config/tratamientos", json={"nombre": "Control", "duracion_min": 15}
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["precio_referencia_centavos"] is None
    url = "/api/config/tratamientos/" + data["id"]
    assert (await client.get(url)).status_code == 200
    updated = await client.patch(url, json={"precio_referencia_centavos": 250000})
    assert updated.status_code == 200
    assert updated.json()["precio_referencia_centavos"] == 250000
    assert (await client.patch(url, json={"precio_referencia_centavos": None})).json()[
        "precio_referencia_centavos"
    ] is None
    assert (await client.get("/api/config/tratamientos")).json()["total"] == 1
    assert (await client.delete(url)).status_code == 204
    assert (await client.get("/api/config/tratamientos?activo=false")).json()["total"] == 1
    assert (await client.patch(url, json={"activo": True})).json()["deleted_at"] is None


async def test_cambio_tratamiento_conserva_turnos(config_client, session):
    client, context = config_client
    _, treatment, turnos = await _schedule(session, context)
    original = (turnos[0].inicio, turnos[0].fin, turnos[0].tratamiento_id)
    response = await client.patch(
        f"/api/config/tratamientos/{treatment.id}",
        json={
            "duracion_min": 60,
            "precio_referencia_centavos": 750000,
            "activo": False,
        },
    )
    assert response.status_code == 200
    await session.refresh(turnos[0])
    assert (turnos[0].inicio, turnos[0].fin, turnos[0].tratamiento_id) == original


@pytest.mark.parametrize("value", [0, -1, 2.5, True, 2147483648])
async def test_tratamiento_duracion_invalida_http(config_client, value):
    client, _ = config_client
    response = await client.post(
        "/api/config/tratamientos", json={"nombre": "Demo", "duracion_min": value}
    )
    assert response.status_code == 422


async def test_crud_bloqueo_y_patch_combinado(config_client, session):
    client, context = config_client
    sillones, _, _ = await _schedule(session, context)
    response = await client.post(
        "/api/config/bloqueos",
        json={
            "sillon_id": str(sillones[0].id),
            "desde": "2026-12-02T10:00:00-03:00",
            "hasta": "2026-12-02T11:00:00-03:00",
            "motivo": "Mantenimiento demo",
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["warnings"] == []
    url = "/api/config/bloqueos/" + data["id"]
    assert (await client.get(url)).json()["sillon_id"] == str(sillones[0].id)
    invalid = await client.patch(url, json={"desde": "2026-12-02T12:00:00-03:00"})
    assert invalid.status_code == 422
    assert (await client.get(url)).json()["desde"] == data["desde"]
    updated = await client.patch(url, json={"sillon_id": None, "motivo": "General"})
    assert updated.status_code == 200
    assert updated.json()["sillon_id"] is None
    assert (await client.get("/api/config/bloqueos")).json()["total"] == 1
    assert (await client.delete(url)).status_code == 204
    assert (await client.get("/api/config/bloqueos?activo=false")).json()["total"] == 1
    restored = await client.patch(url, json={"activo": True})
    assert restored.json()["deleted_at"] is None
    events = (
        await session.scalars(
            select(ConfigAudit)
            .where(ConfigAudit.recurso == "bloqueo")
            .order_by(ConfigAudit.created_at)
        )
    ).all()
    assert [event.accion for event in events] == ["crear", "actualizar", "desactivar", "reactivar"]
    assert events[1].antes["sillon_id"] == str(sillones[0].id)
    assert events[1].despues["sillon_id"] is None


@pytest.mark.parametrize("scope,expected", [("general", 2), ("primero", 1), ("segundo", 1)])
async def test_bloqueo_advierte_pero_no_modifica_turnos(config_client, session, scope, expected):
    client, context = config_client
    sillones, _, turnos = await _schedule(session, context)
    original = [(t.id, t.inicio, t.fin, t.estado) for t in turnos]
    sillon_id = None if scope == "general" else str(sillones[0 if scope == "primero" else 1].id)
    response = await client.post(
        "/api/config/bloqueos",
        json={
            "sillon_id": sillon_id,
            "desde": "2026-12-01T10:00:00-03:00",
            "hasta": "2026-12-01T10:30:00-03:00",
            "motivo": "Bloqueo demo",
        },
    )
    assert response.status_code == 201
    assert response.json()["warnings"] == [{"code": "TURNOS_SOLAPADOS", "cantidad": expected}]
    for t in turnos:
        await session.refresh(t)
    assert [(t.id, t.inicio, t.fin, t.estado) for t in turnos] == original
    # También advierte al modificar un bloqueo existente.
    patched = await client.patch(
        "/api/config/bloqueos/" + response.json()["id"], json={"motivo": "Actualizado"}
    )
    assert patched.json()["warnings"][0]["cantidad"] == expected


@pytest.mark.parametrize("case", ["adyacente", "otro-sillon", "cancelado", "ausente", "inactivo"])
async def test_bloqueo_excluye_no_solapados(config_client, session, case):
    client, context = config_client
    sillones, _, turnos = await _schedule(session, context)
    inicio, fin = "2026-12-01T10:00:00-03:00", "2026-12-01T10:30:00-03:00"
    if case == "adyacente":
        inicio, fin = "2026-12-01T10:30:00-03:00", "2026-12-01T11:00:00-03:00"
    elif case == "otro-sillon":
        from datetime import timedelta

        turnos[0].inicio += timedelta(days=1)
        turnos[0].fin += timedelta(days=1)
    elif case == "inactivo":
        turnos[0].is_active = False
    else:
        turnos[0].estado = case
    await session.commit()
    response = await client.post(
        "/api/config/bloqueos",
        json={
            "sillon_id": str(sillones[0].id),
            "desde": inicio,
            "hasta": fin,
            "motivo": "Demo",
        },
    )
    assert response.status_code == 201
    assert response.json()["warnings"] == []


async def test_bloqueo_referencia_inexistente_inactiva_y_naive(config_client, session):
    client, context = config_client
    sillones, _, _ = await _schedule(session, context)
    base = {
        "desde": "2026-12-01T10:00:00-03:00",
        "hasta": "2026-12-01T11:00:00-03:00",
        "motivo": "Demo",
    }
    assert (
        await client.post("/api/config/bloqueos", json=base | {"sillon_id": str(uuid4())})
    ).status_code == 404
    sillones[0].is_active = False
    await session.commit()
    assert (
        await client.post("/api/config/bloqueos", json=base | {"sillon_id": str(sillones[0].id)})
    ).status_code == 422
    assert (
        await client.post("/api/config/bloqueos", json=base | {"desde": "2026-12-01T10:00:00"})
    ).status_code == 422


async def test_auditoria_sillon_snapshots_y_noop(config_client, session):
    client, context = config_client
    response = await client.post(
        "/api/config/sillones",
        json={
            "consultorio_id": context["consultorio_id"],
            "nombre": "Demo",
        },
    )
    url = "/api/config/sillones/" + response.json()["id"]
    await client.patch(url, json={"nombre": "Modificado"})
    await client.delete(url)
    await client.delete(url)
    await client.patch(url, json={"activo": True})
    events = list(
        (await session.scalars(select(ConfigAudit).order_by(ConfigAudit.created_at))).all()
    )
    assert [e.accion for e in events] == ["crear", "actualizar", "desactivar", "reactivar"]
    assert all(e.actor_id == context["actors"]["secretaria"]["id"] for e in events)
    assert events[0].antes is None
    assert events[1].antes["nombre"] == "Demo"
    assert events[1].despues["nombre"] == "Modificado"
    assert events[2].despues["activo"] is False
    assert events[3].despues["deleted_at"] is None
    assert all("password_hash" not in str(e.despues) for e in events)


async def test_auditoria_fallida_revierte_catalogo(config_client, session, engine):
    client, context = config_client
    response = await client.post(
        "/api/config/sillones",
        json={
            "consultorio_id": context["consultorio_id"],
            "nombre": "Nombre anterior",
        },
    )
    url = "/api/config/sillones/" + response.json()["id"]
    suffix = uuid4().hex
    function, trigger = f"test_reject_audit_{suffix}", f"test_reject_audit_{suffix}"
    async with engine.begin() as connection:
        await connection.execute(
            text(f"""
            CREATE FUNCTION {function}() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN RAISE EXCEPTION 'Fallo de test' USING ERRCODE='23514'; END $$;
        """)
        )
        await connection.execute(
            text(f"""
            CREATE TRIGGER {trigger} BEFORE INSERT ON config_audit
            FOR EACH ROW EXECUTE FUNCTION {function}();
        """)
        )
    try:
        failed = await client.patch(url, json={"nombre": "No debe persistir"})
        assert failed.status_code >= 400
        assert (await client.get(url)).json()["nombre"] == "Nombre anterior"
        failed_create = await client.post(
            "/api/config/sillones",
            json={
                "consultorio_id": context["consultorio_id"],
                "nombre": "No crear",
            },
        )
        assert failed_create.status_code >= 400
        assert (await client.get("/api/config/sillones")).json()["total"] == 1
        events = list((await session.scalars(select(ConfigAudit))).all())
        assert len(events) == 1
    finally:
        # Liberar AccessShareLock de la consulta de eventos antes del DDL de limpieza.
        await session.rollback()
        async with engine.begin() as connection:
            await connection.execute(text(f"DROP TRIGGER {trigger} ON config_audit"))
            await connection.execute(text(f"DROP FUNCTION {function}()"))


@pytest.mark.parametrize("method", ["GET", "PATCH", "DELETE"])
@pytest.mark.parametrize("resource", ["sillones", "tratamientos", "bloqueos"])
async def test_recurso_inexistente_404(config_client, method, resource):
    client, _ = config_client
    response = await client.request(
        method, f"/api/config/{resource}/{uuid4()}", json={} if method == "PATCH" else None
    )
    assert response.status_code == 404


@pytest.mark.parametrize("query", ["page=0", "page_size=0", "page_size=101"])
@pytest.mark.parametrize("resource", ["sillones", "tratamientos", "bloqueos"])
async def test_paginacion_limites(config_client, query, resource):
    client, _ = config_client
    assert (await client.get(f"/api/config/{resource}?" + query)).status_code == 422


def test_openapi_config_contratos():
    schema = app.openapi()
    for resource in ("sillones", "tratamientos", "bloqueos"):
        collection = schema["paths"][f"/api/config/{resource}"]
        assert "201" in collection["post"]["responses"]
        parameters = {p["name"]: p["schema"] for p in collection["get"]["parameters"]}
        assert parameters["page"]["default"] == 1
        assert parameters["page_size"]["default"] == 20
        assert parameters["page_size"]["maximum"] == 100
        assert parameters["activo"]["default"] is True
        item = schema["paths"][f"/api/config/{resource}/{{entity_id}}"]
        assert {"get", "patch", "delete"} <= item.keys()
    assert schema["components"]["schemas"]["SillonCreate"]["additionalProperties"] is False


@pytest.mark.parametrize("role", ["paciente", "secretaria-inactiva"])
async def test_config_usa_rol_y_estado_vigentes(config_client, session, role):
    client, context = config_client
    actor = context["actors"]["paciente" if role == "paciente" else "secretaria"]
    if role == "secretaria-inactiva":
        stored = await session.get(Usuario, actor["id"])
        stored.is_active = False
        await session.commit()
    token = create_access_token(actor["id"], ["secretaria"], "demo@example.com")[0]
    response = await client.get(
        "/api/config/sillones", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == (403 if role == "paciente" else 401)


@pytest.mark.parametrize("invalid", ["actor", "recurso", "accion", "naive"])
async def test_auditoria_restricciones_motor(session, invalid):
    from sqlalchemy.exc import SQLAlchemyError

    actor = Usuario(email="audit.demo@example.com", rol="secretaria", password_hash="ficticio")
    session.add(actor)
    await session.flush()
    values = {"actor_id": actor.id, "recurso": "sillon", "recurso_id": uuid4(), "accion": "crear"}
    if invalid == "actor":
        values["actor_id"] = uuid4()
    elif invalid == "naive":
        values["created_at"] = datetime(2026, 12, 1)
    else:
        values[invalid] = "invalido"
    session.add(ConfigAudit(**values))
    with pytest.raises(SQLAlchemyError):
        await session.flush()
    await session.rollback()


async def test_paginacion_estable_y_referencias(config_client, session):
    client, context = config_client
    ids = []
    for name in ("Primero", "Segundo", "Tercero"):
        response = await client.post(
            "/api/config/sillones",
            json={
                "nombre": name,
                "consultorio_id": context["consultorio_id"],
            },
        )
        ids.append(response.json()["id"])
    first = (await client.get("/api/config/sillones?page_size=2")).json()
    second = (await client.get("/api/config/sillones?page_size=2&page=2")).json()
    assert first["total"] == second["total"] == 3
    assert [r["id"] for r in first["items"] + second["items"]] == ids
    assert (
        await client.post(
            "/api/config/sillones",
            json={
                "nombre": "Falta referencia",
                "consultorio_id": str(uuid4()),
            },
        )
    ).status_code == 404
    consultorio = await session.get(Consultorio, context["consultorio_id"])
    consultorio.is_active = False
    await session.commit()
    assert (
        await client.post(
            "/api/config/sillones",
            json={
                "nombre": "Inactivo",
                "consultorio_id": context["consultorio_id"],
            },
        )
    ).status_code == 422
    assert (
        await client.patch(
            "/api/config/sillones/" + ids[0],
            json={
                "consultorio_id": context["consultorio_id"],
            },
        )
    ).status_code == 422


async def _schedule(session, context):
    from datetime import timedelta
    from uuid import UUID

    sillones = [
        Sillon(nombre=f"Demo {i}", consultorio_id=UUID(context["consultorio_id"])) for i in (1, 2)
    ]
    treatment = Tratamiento(
        nombre="Control demo", duracion_min=30, precio_referencia_centavos=500000
    )
    patient = Paciente(
        usuario_id=context["actors"]["paciente"]["id"],
        nombre="Paciente ficticio",
        telefono="+54 9 11 0000-0000",
    )
    session.add_all([*sillones, treatment, patient])
    await session.flush()
    start = datetime(2026, 12, 1, 13, 0, tzinfo=UTC)
    turnos = [
        Turno(
            sillon_id=sillon.id,
            paciente_id=patient.id,
            tratamiento_id=treatment.id,
            inicio=start,
            fin=start + timedelta(minutes=30),
        )
        for sillon in sillones
    ]
    session.add_all(turnos)
    await session.commit()
    return sillones, treatment, turnos


async def test_baja_sillon_conserva_historial(config_client, session):
    client, context = config_client
    sillones, _, turnos = await _schedule(session, context)
    original = (turnos[0].inicio, turnos[0].fin, turnos[0].sillon_id)
    assert (await client.delete(f"/api/config/sillones/{sillones[0].id}")).status_code == 204
    await session.refresh(turnos[0])
    assert (turnos[0].inicio, turnos[0].fin, turnos[0].sillon_id) == original
    await session.refresh(sillones[0])
    assert sillones[0].is_active is False


@pytest.mark.parametrize(
    "extra", [{"nombre": None}, {"actor_id": "falso"}, {"created_at": "falso"}]
)
async def test_sillon_rechaza_null_y_metadatos(config_client, extra):
    client, context = config_client
    response = await client.post(
        "/api/config/sillones",
        json={
            "nombre": "Demo",
            "consultorio_id": context["consultorio_id"],
            **extra,
        },
    )
    assert response.status_code == 422


def test_schema_sillon_patch_distingue_omitido_de_null():
    from pydantic import ValidationError

    from app.schemas.config import SillonCreate, SillonPatch

    payload = SillonCreate(consultorio_id=str(uuid4()), nombre="  Sillón demo  ")
    assert payload.nombre == "Sillón demo"
    assert SillonPatch().model_dump(exclude_unset=True) == {}
    for invalid in (
        {"nombre": None},
        {"nombre": " "},
        {"nombre": "x" * 81},
        {"consultorio_id": None},
        {"activo": None},
        {"actor_id": str(uuid4())},
    ):
        with pytest.raises(ValidationError):
            SillonPatch.model_validate(invalid)


@pytest.mark.parametrize(
    "field,value",
    [
        ("duracion_min", 0),
        ("duracion_min", -1),
        ("duracion_min", 1.5),
        ("duracion_min", True),
        ("duracion_min", 2147483648),
        ("precio_referencia_centavos", -1),
        ("precio_referencia_centavos", 10.5),
        ("precio_referencia_centavos", False),
        ("precio_referencia_centavos", 2147483648),
    ],
)
def test_schema_tratamiento_numeros_estrictos(field, value):
    from pydantic import ValidationError

    from app.schemas.config import TratamientoCreate, TratamientoPatch

    data = {"nombre": "Control", "duracion_min": 15, field: value}
    with pytest.raises(ValidationError):
        TratamientoCreate.model_validate(data)
    with pytest.raises(ValidationError):
        TratamientoPatch.model_validate({field: value})


def test_schema_tratamiento_precio_nullable():
    from app.schemas.config import TratamientoCreate, TratamientoPatch

    created = TratamientoCreate(nombre="Control", duracion_min=15)
    assert created.precio_referencia_centavos is None
    assert TratamientoPatch().model_dump(exclude_unset=True) == {}
    assert TratamientoPatch(precio_referencia_centavos=None).model_dump(exclude_unset=True) == {
        "precio_referencia_centavos": None,
    }


@pytest.mark.parametrize(
    "desde,hasta",
    [
        ("2026-12-01T10:00:00", "2026-12-01T11:00:00-03:00"),
        ("2026-12-01T10:00:00-03:00", "2026-12-01T10:00:00-03:00"),
        ("2026-12-01T11:00:00-03:00", "2026-12-01T10:00:00-03:00"),
    ],
)
def test_schema_bloqueo_rechaza_naive_y_rango(desde, hasta):
    from pydantic import ValidationError

    from app.schemas.config import BloqueoCreate

    with pytest.raises(ValidationError):
        BloqueoCreate(desde=desde, hasta=hasta, motivo="Mantenimiento ficticio")


def test_schema_bloqueo_alcance_nullable():
    from app.schemas.config import BloqueoCreate, BloqueoPatch

    data = BloqueoCreate(
        desde="2026-12-01T10:00:00-03:00",
        hasta="2026-12-01T11:00:00-03:00",
        motivo="  Mantenimiento demo  ",
    )
    assert data.sillon_id is None
    assert data.motivo == "Mantenimiento demo"
    assert BloqueoPatch(sillon_id=None).model_dump(exclude_unset=True) == {"sillon_id": None}


async def test_auditoria_persiste_autor_y_fecha(session):
    from app.models import ConfigAudit

    actor = Usuario(email="config.demo@example.com", rol="secretaria", password_hash="ficticio")
    session.add(actor)
    await session.flush()
    event = ConfigAudit(
        actor_id=actor.id,
        recurso="sillon",
        recurso_id=uuid4(),
        accion="crear",
        antes=None,
        despues={"nombre": "Sillón ficticio"},
    )
    session.add(event)
    await session.commit()
    loaded = (
        await session.execute(select(ConfigAudit).where(ConfigAudit.id == event.id))
    ).scalar_one()
    assert loaded.actor_id == actor.id
    assert loaded.accion == "crear"
    assert loaded.antes is None
    assert loaded.despues == {"nombre": "Sillón ficticio"}
    assert loaded.created_at.tzinfo is not None
    assert loaded.created_at <= datetime.now(UTC)
