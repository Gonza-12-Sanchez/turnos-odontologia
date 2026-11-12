"""C-09: cobros locales (tareas 3.1-3.4)."""

from asyncio import gather
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api import deps
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


@pytest.fixture
async def c09_cobros_client(engine, session, monkeypatch):
    monkeypatch.setattr(
        deps, "get_session_factory", lambda: async_sessionmaker(engine, expire_on_commit=False)
    )
    monkeypatch.setattr(redis_client, "get_redis", lambda: _FakeRedis())
    consultorio = Consultorio(nombre="Consultorio Cobros")
    session.add(consultorio)
    await session.flush()
    sillon = Sillon(consultorio_id=consultorio.id, nombre="Sillon Cobros", is_active=True)
    session.add(sillon)
    tratamiento = Tratamiento(
        nombre="Limpieza",
        duracion_min=30,
        precio_referencia_centavos=10000,
        sena_politica="deshabilitada",
        sena_centavos=None,
    )
    session.add(tratamiento)
    await session.flush()
    usuario = Usuario(email="secre.cobros@example.com", rol="secretaria", password_hash="ficticio")
    session.add(usuario)
    await session.flush()
    paciente = Paciente(usuario_id=usuario.id, nombre="Paciente Cobros", telefono="1112345678")
    session.add(paciente)
    await session.flush()
    token = create_access_token(usuario.id, ["secretaria"], usuario.email)[0]
    ahora = datetime.now(UTC)
    turno = Turno(
        paciente_id=paciente.id,
        sillon_id=sillon.id,
        tratamiento_id=tratamiento.id,
        inicio=ahora + timedelta(days=1),
        fin=ahora + timedelta(days=1, minutes=30),
        estado="reservado",
        origen="mostrador",
    )
    session.add(turno)
    await session.flush()
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
                "turno_id": str(turno.id),
                "usuario_id": str(usuario.id),
                "precio_referencia_centavos": 10000,
            },
        )


async def _post_cobro(
    client, turno_id, monto, medio="efectivo", tipo="total", override_motivo=None, idem=None
):
    payload = {
        "turno_id": turno_id,
        "monto_centavos": monto,
        "medio": medio,
        "tipo": tipo,
    }
    if override_motivo:
        payload["override_motivo"] = override_motivo
    headers = {}
    if idem:
        headers["Idempotency-Key"] = idem
    return await client.post("/cobros", json=payload, headers=headers)


# --- RED: endpoint /cobros no existe aún ---


async def test_cobro_feliz_efectivo(c09_cobros_client):
    client, ctx = c09_cobros_client
    response = await _post_cobro(client, ctx["turno_id"], 10000, idem=str(uuid4()))
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["cobro"]["monto_centavos"] == 10000
    assert data["cobro"]["medio"] == "efectivo"
    assert data["cobro"]["tipo"] == "total"
    assert data["total_cobrado_centavos"] == 10000
    assert data["sena_acumulada_centavos"] == 0
    assert data["saldo_referencia_centavos"] == 0
    assert data["facturacion_electronica"] is False


@pytest.mark.parametrize("medio", ["efectivo", "transferencia", "mercadopago"])
async def test_cobro_conciliacion_sena(c09_cobros_client, medio):
    client, ctx = c09_cobros_client
    # Primero seña de 3000 (tipo sena no tiene cheque MONTO_DIFIERE)
    r1 = await _post_cobro(client, ctx["turno_id"], 3000, tipo="sena", idem=str(uuid4()))
    assert r1.status_code == 201, r1.text
    # Luego cierre de 7000 -> total 10000, saldo 0
    clave = str(uuid4())
    r2 = await _post_cobro(client, ctx["turno_id"], 7000, medio=medio, idem=clave)
    assert r2.status_code == 201, r2.text
    data = r2.json()
    assert data["cobro"]["medio"] == medio
    replay = await _post_cobro(client, ctx["turno_id"], 7000, medio=medio, idem=clave)
    assert replay.status_code == 200
    assert replay.json() == data
    assert data["sena_acumulada_centavos"] == 3000
    assert data["total_cobrado_centavos"] == 10000
    assert data["saldo_referencia_centavos"] == 0


async def test_cobro_monto_difiere_sin_override(c09_cobros_client):
    client, ctx = c09_cobros_client
    response = await _post_cobro(client, ctx["turno_id"], 7000, idem=str(uuid4()))
    assert response.status_code == 409, response.text
    data = response.json()
    assert data["detail"]["code"] == "MONTO_DIFIERE"
    assert data["detail"]["esperado_centavos"] == 10000
    assert data["detail"]["recibido_centavos"] == 7000


async def test_cobro_monto_difiere_con_override(c09_cobros_client):
    client, ctx = c09_cobros_client
    response = await _post_cobro(
        client,
        ctx["turno_id"],
        7000,
        override_motivo="Descuento por pago contado",
        idem=str(uuid4()),
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["cobro"]["monto_centavos"] == 7000
    assert data["saldo_referencia_centavos"] == 3000
    assert any(w["code"] == "MONTO_DIFIERE_OVERRIDE" for w in data["warnings"])


async def test_cobro_sena_duplicada_rechazada(c09_cobros_client):
    client, ctx = c09_cobros_client
    await _post_cobro(client, ctx["turno_id"], 3000, tipo="sena", idem=str(uuid4()))
    response = await _post_cobro(client, ctx["turno_id"], 2000, tipo="sena", idem=str(uuid4()))
    assert response.status_code == 409, response.text
    data = response.json()
    assert data["detail"]["code"] == "SENA_DUPLICADA"


async def test_cobro_anonimo_401(engine, session, monkeypatch):
    monkeypatch.setattr(
        deps, "get_session_factory", lambda: async_sessionmaker(engine, expire_on_commit=False)
    )
    monkeypatch.setattr(redis_client, "get_redis", lambda: _FakeRedis())
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="https://test") as client:
        response = await _post_cobro(client, str(uuid4()), 1000)
        assert response.status_code == 401, response.text


async def test_cobro_paciente_403(c09_cobros_client, engine, session, monkeypatch):
    monkeypatch.setattr(
        deps, "get_session_factory", lambda: async_sessionmaker(engine, expire_on_commit=False)
    )
    monkeypatch.setattr(redis_client, "get_redis", lambda: _FakeRedis())
    paciente = Usuario(email="pac.cobros@example.com", rol="paciente", password_hash="ficticio")
    session.add(paciente)
    await session.flush()
    token = create_access_token(paciente.id, ["paciente"], paciente.email)[0]
    await session.commit()
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(
        transport=transport,
        base_url="https://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as client:
        response = await _post_cobro(client, str(uuid4()), 1000)
        assert response.status_code == 403, response.text


async def test_cobro_monto_float_rechazado(c09_cobros_client):
    client, ctx = c09_cobros_client
    response = await client.post(
        "/cobros",
        json={
            "turno_id": ctx["turno_id"],
            "monto_centavos": 12.5,
            "medio": "efectivo",
            "tipo": "total",
        },
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == 422, response.text


async def test_cobro_monto_booleano_rechazado(c09_cobros_client):
    client, ctx = c09_cobros_client
    response = await client.post(
        "/cobros",
        json={
            "turno_id": ctx["turno_id"],
            "monto_centavos": True,
            "medio": "efectivo",
            "tipo": "total",
        },
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == 422, response.text


async def test_cobro_medio_invalido_rechazado(c09_cobros_client):
    client, ctx = c09_cobros_client
    response = await client.post(
        "/cobros",
        json={
            "turno_id": ctx["turno_id"],
            "monto_centavos": 1000,
            "medio": "tarjeta",
            "tipo": "total",
        },
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == 422, response.text


async def test_cobro_idempotencia_replay(c09_cobros_client):
    client, ctx = c09_cobros_client
    clave = str(uuid4())
    r1 = await _post_cobro(client, ctx["turno_id"], 10000, idem=clave)
    assert r1.status_code == 201, r1.text
    # Replay misma clave y mismo payload -> mismo cobro, sin duplicar
    r2 = await _post_cobro(client, ctx["turno_id"], 10000, idem=clave)
    assert r2.status_code == 200, r2.text
    data = r2.json()
    assert data == r1.json()
    resultado = await client.get("/cobros/operacion", headers={"Idempotency-Key": clave})
    assert resultado.status_code == 200
    assert resultado.json() == data
    ausente = await client.get("/cobros/operacion", headers={"Idempotency-Key": str(uuid4())})
    assert ausente.json() is None
    # No hay segundo cobro en el turno
    rows = await client.get(f"/cobros?turno_id={ctx['turno_id']}")
    assert rows.status_code == 200
    assert len(rows.json()) == 1


async def test_cobro_requiere_clave(c09_cobros_client):
    client, ctx = c09_cobros_client
    response = await _post_cobro(client, ctx["turno_id"], 10000)
    assert response.status_code == 422
    assert (await client.get(f"/cobros?turno_id={ctx['turno_id']}")).json() == []


@pytest.mark.parametrize("misma_clave,esperado", [(True, [200, 201]), (False, [201, 409])])
async def test_cierre_concurrente(c09_cobros_client, misma_clave, esperado):
    client, ctx = c09_cobros_client
    turno = ctx["turno_id"]
    primera = str(uuid4())
    segunda = primera if misma_clave else str(uuid4())
    respuestas = await gather(
        _post_cobro(client, turno, 10000, idem=primera),
        _post_cobro(client, turno, 10000, idem=segunda),
    )
    assert sorted(response.status_code for response in respuestas) == esperado
    if misma_clave:
        assert respuestas[0].json() == respuestas[1].json()
    assert len((await client.get(f"/cobros?turno_id={turno}")).json()) == 1
    resumen = (await client.get(f"/cobros/resumen/{turno}")).json()
    assert resumen["cerrado"] is True
    assert resumen["total_cobrado_centavos"] == 10000
    assert resumen["saldo_referencia_centavos"] == 0


async def test_cobro_idempotencia_clave_diferente_payload(c09_cobros_client):
    client, ctx = c09_cobros_client
    clave = str(uuid4())
    r1 = await _post_cobro(client, ctx["turno_id"], 10000, idem=clave)
    assert r1.status_code == 201, r1.text
    # Misma clave, monto distinto -> 409
    r2 = await _post_cobro(client, ctx["turno_id"], 8000, idem=clave)
    assert r2.status_code == 409, r2.text
    data = r2.json()
    assert data["detail"]["code"] == "IDEMPOTENCIA_CLAVE_DIFERENTE"


async def test_cobro_cierre_por_cero_no_crea(c09_cobros_client):
    client, ctx = c09_cobros_client
    response = await _post_cobro(client, ctx["turno_id"], 0, idem=str(uuid4()))
    assert response.status_code == 422, response.text


async def test_cobros_listado(c09_cobros_client):
    client, ctx = c09_cobros_client
    await _post_cobro(client, ctx["turno_id"], 10000, idem=str(uuid4()))
    rows = await client.get(f"/cobros?turno_id={ctx['turno_id']}")
    assert rows.status_code == 200, rows.text
    data = rows.json()
    assert len(data) == 1
    assert data[0]["monto_centavos"] == 10000
    assert data[0]["turno_id"] == ctx["turno_id"]
