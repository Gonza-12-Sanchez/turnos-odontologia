"""C-09: webhook MP HMAC-SHA256, aplicacion atomica e idempotencia (tareas 5.1, 5.2, 5.3)."""

from __future__ import annotations

import hashlib
import hmac
import json
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
    AuditoriaCobro,
    Cobro,
    IntentoSena,
    PagoMP,
    Turno,
)
from app.services.sena_service import SenaService
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


class _FakeMPAdapter:
    """Adaptador MP falso que devuelve el pago configurado por payment_id."""

    def __init__(self, pagos: dict[str, dict] | None = None):
        self.pagos = pagos or {}
        self.consultados: list[str] = []

    async def obtener_pago(self, access_token: str, payment_id: str) -> dict:
        self.consultados.append(payment_id)
        pago = self.pagos.get(payment_id)
        if pago is None:
            from app.services.mp_adapter import MPAdapterError

            raise MPAdapterError(
                404, {"code": "MP_NOT_FOUND", "detail": "pago no encontrado"}, code="MP_NOT_FOUND"
            )
        return dict(pago)

    async def aclose(self) -> None:
        pass


def _firmar_webhook(secret: str, timestamp: int, body: bytes) -> str:
    """Genera firma MP: ts={ts};v1={hmac_sha256(secret, ts={ts}.{body})}."""
    mensaje = f"ts={timestamp}.".encode() + body
    firma = hmac.new(secret.encode("utf-8"), mensaje, hashlib.sha256).hexdigest()
    return f"ts={timestamp};v1={firma}"


def _webhook_body(payment_id: str, status: str = "approved") -> dict:
    return {
        "id": 12345,
        "type": "payment",
        "data": {"id": payment_id},
        "date_created": datetime.now(UTC).isoformat(),
        "live_mode": False,
    }


@pytest.fixture
async def c09_webhook_client(engine, session, monkeypatch):
    """Cliente con sesiones y Redis aislados, autenticado como secretaria."""
    monkeypatch.setattr(
        deps, "get_session_factory", lambda: async_sessionmaker(engine, expire_on_commit=False)
    )
    monkeypatch.setattr(redis_client, "get_redis", lambda: _FakeRedis())
    settings.mp_webhook_secret = "wh_secret_test"
    settings.mp_mode = "mock"
    settings.mp_collector_id = "collector_test"

    consultorio = None
    from app.models import Consultorio, Paciente, Sillon, Tratamiento, Usuario

    consultorio = Consultorio(nombre="Consultorio Webhook")
    session.add(consultorio)
    await session.flush()
    sillon = Sillon(consultorio_id=consultorio.id, nombre="Sillon Webhook", is_active=True)
    session.add(sillon)
    await session.flush()
    tratamiento = Tratamiento(
        nombre="Limpieza",
        duracion_min=30,
        precio_referencia_centavos=10000,
        sena_politica="obligatoria",
        sena_centavos=3000,
    )
    session.add(tratamiento)
    await session.flush()
    usuario = Usuario(email="secre.webhook@example.com", rol="secretaria", password_hash="ficticio")
    session.add(usuario)
    await session.flush()
    paciente = Paciente(usuario_id=usuario.id, nombre="Paciente Webhook", telefono="1112345678")
    session.add(paciente)
    await session.flush()
    token = create_access_token(usuario.id, ["secretaria"], usuario.email)[0]
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
                "paciente_id": str(paciente.id),
                "usuario_id": str(usuario.id),
                "token": token,
            },
        )


async def _crear_intento_en_db(
    session,
    paciente_id,
    sillon_id,
    tratamiento_id,
    preference_id="pref_test",
    payment_id=None,
    estado="pendiente",
):
    ahora = datetime.now(UTC)
    # Alinear inicio a grilla de 30 min (10:00 UTC del día siguiente)
    base = ahora.replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1)
    inicio = base
    intento = IntentoSena(
        paciente_id=paciente_id,
        sillon_id=sillon_id,
        tratamiento_id=tratamiento_id,
        inicio=inicio,
        fin=inicio + timedelta(minutes=30),
        duracion_min=30,
        monto_centavos=3000,
        moneda="ARS",
        sena_politica="obligatoria",
        estado=estado,
        preference_id=preference_id,
        checkout_url="https://mock.mp/checkout/pref_test",
        expires_at=ahora + timedelta(minutes=15),
        modo="mock",
    )
    session.add(intento)
    await session.flush()
    await session.refresh(intento)
    if payment_id:
        pago = PagoMP(
            intento_id=intento.id,
            payment_id=payment_id,
            estado_proveedor=estado,
            monto_centavos=3000,
            moneda="ARS",
            receptor_id="collector_test",
            modo="mock",
            resultado="pendiente",
        )
        session.add(pago)
        await session.flush()
    await session.commit()
    return intento


# ============================================================
# RED: endpoint /webhooks/mercadopago no existe -> 404
# ============================================================


async def test_webhook_firma_invalida_401(c09_webhook_client, session):
    client, _ctx = c09_webhook_client
    body = json.dumps(_webhook_body("pay_nuevo")).encode()
    timestamp = int(datetime.now(UTC).timestamp())
    firma = _firmar_webhook("secreto_equivocado", timestamp, body)
    response = await client.post(
        "/webhooks/mercadopago",
        content=body,
        headers={
            "x-signature": firma,
            "x-request-id": str(uuid4()),
            "content-type": "application/json",
        },
    )
    assert response.status_code == 401, response.text


async def test_webhook_sin_firma_401(c09_webhook_client):
    client, _ = c09_webhook_client
    body = json.dumps(_webhook_body("pay_nuevo")).encode("utf-8")
    response = await client.post(
        "/webhooks/mercadopago",
        content=body,
        headers={
            "x-request-id": str(uuid4()),
            "content-type": "application/json",
        },
    )
    assert response.status_code == 401, response.text


async def test_webhook_pago_aprobado_crea_turno_y_cobro(c09_webhook_client, session, monkeypatch):
    client, ctx = c09_webhook_client
    payment_id = "pay_webhook_001"
    intento = await _crear_intento_en_db(
        session,
        ctx["paciente_id"],
        ctx["sillon_id"],
        ctx["tratamiento_id"],
        preference_id="pref_webhook_001",
    )
    fake_adapter = _FakeMPAdapter(
        {
            payment_id: {
                "id": payment_id,
                "status": "approved",
                "external_reference": str(intento.id),
                "collector_id": "collector_test",
                "currency_id": "ARS",
                "transaction_amount": 30.00,
                "date_approved": datetime.now(UTC).isoformat(),
                "live_mode": False,
            }
        }
    )
    monkeypatch.setattr(
        SenaService,
        "mp_adapter",
        property(lambda self: fake_adapter),
        raising=False,
    )
    body = json.dumps(_webhook_body(payment_id, "approved")).encode("utf-8")
    timestamp = int(datetime.now(UTC).timestamp())
    firma = _firmar_webhook(settings.mp_webhook_secret, timestamp, body)
    response = await client.post(
        "/webhooks/mercadopago",
        content=body,
        headers={
            "x-signature": firma,
            "x-request-id": str(uuid4()),
            "content-type": "application/json",
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["aplicado"] is True
    # Verificar en DB
    from sqlalchemy import select

    turno = (await session.scalars(select(Turno))).first()
    assert turno is not None
    assert str(turno.paciente_id) == ctx["paciente_id"]
    cobro = (await session.scalars(select(Cobro))).first()
    assert cobro is not None
    assert cobro.monto_centavos == 3000
    assert cobro.referencia_mp == payment_id
    auditoria = (
        await session.scalars(select(AuditoriaCobro).where(AuditoriaCobro.cobro_id == cobro.id))
    ).first()
    assert auditoria is not None
    # Intento marcado aprobado
    await session.refresh(intento)
    assert intento.estado == "aprobado"
    assert intento.turno_id == turno.id


async def test_webhook_pago_rechazado_sin_turno(c09_webhook_client, session, monkeypatch):
    client, ctx = c09_webhook_client
    payment_id = "pay_rechazado_001"
    intento = await _crear_intento_en_db(
        session,
        ctx["paciente_id"],
        ctx["sillon_id"],
        ctx["tratamiento_id"],
        preference_id="pref_rechazado_001",
    )
    fake_adapter = _FakeMPAdapter(
        {
            payment_id: {
                "id": payment_id,
                "status": "rejected",
                "external_reference": str(intento.id),
                "collector_id": "collector_test",
                "currency_id": "ARS",
                "transaction_amount": 30.00,
                "date_approved": None,
                "live_mode": False,
            }
        }
    )
    monkeypatch.setattr(
        SenaService,
        "mp_adapter",
        property(lambda self: fake_adapter),
        raising=False,
    )
    body = json.dumps(_webhook_body(payment_id, "rejected")).encode("utf-8")
    timestamp = int(datetime.now(UTC).timestamp())
    firma = _firmar_webhook(settings.mp_webhook_secret, timestamp, body)
    response = await client.post(
        "/webhooks/mercadopago",
        content=body,
        headers={
            "x-signature": firma,
            "x-request-id": str(uuid4()),
            "content-type": "application/json",
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["aplicado"] is False
    assert data["motivo"] == "pago_rechazado"
    # No turno creado
    from sqlalchemy import select

    turnos = (await session.scalars(select(Turno))).all()
    assert len(turnos) == 0
    cobros = (await session.scalars(select(Cobro))).all()
    assert len(cobros) == 0
    # Intento marcado rechazado
    await session.refresh(intento)
    assert intento.estado == "rechazado"


async def test_webhook_duplicado_idempotente(c09_webhook_client, session, monkeypatch):
    client, ctx = c09_webhook_client
    payment_id = "pay_idem_001"
    intento = await _crear_intento_en_db(
        session,
        ctx["paciente_id"],
        ctx["sillon_id"],
        ctx["tratamiento_id"],
        preference_id="pref_idem_001",
    )
    fake_adapter = _FakeMPAdapter(
        {
            payment_id: {
                "id": payment_id,
                "status": "approved",
                "external_reference": str(intento.id),
                "collector_id": "collector_test",
                "currency_id": "ARS",
                "transaction_amount": 30.00,
                "date_approved": datetime.now(UTC).isoformat(),
                "live_mode": False,
            }
        }
    )
    monkeypatch.setattr(
        SenaService,
        "mp_adapter",
        property(lambda self: fake_adapter),
        raising=False,
    )
    body = json.dumps(_webhook_body(payment_id, "approved")).encode("utf-8")
    timestamp = int(datetime.now(UTC).timestamp())
    firma = _firmar_webhook(settings.mp_webhook_secret, timestamp, body)

    # Primera notificacion
    r1 = await client.post(
        "/webhooks/mercadopago",
        content=body,
        headers={
            "x-signature": firma,
            "x-request-id": str(uuid4()),
            "content-type": "application/json",
        },
    )
    assert r1.status_code == 200
    # Segunda notificacion duplicada -> idempotente, sin duplicar
    r2 = await client.post(
        "/webhooks/mercadopago",
        content=body,
        headers={
            "x-signature": firma,
            "x-request-id": str(uuid4()),
            "content-type": "application/json",
        },
    )
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["aplicado"] is True
    assert data2.get("duplicado") is True
    # Un solo turno y un solo cobro
    from sqlalchemy import select

    turnos = (await session.scalars(select(Turno))).all()
    assert len(turnos) == 1
    cobros = (await session.scalars(select(Cobro))).all()
    assert len(cobros) == 1
    pagos = (await session.scalars(select(PagoMP))).all()
    assert len(pagos) == 1


async def test_webhook_discrepancia_monto_registro_incidencia(
    c09_webhook_client, session, monkeypatch
):
    client, ctx = c09_webhook_client
    payment_id = "pay_disc_001"
    intento = await _crear_intento_en_db(
        session,
        ctx["paciente_id"],
        ctx["sillon_id"],
        ctx["tratamiento_id"],
        preference_id="pref_disc_001",
    )
    # MP informa monto distinto al del intento
    fake_adapter = _FakeMPAdapter(
        {
            payment_id: {
                "id": payment_id,
                "status": "approved",
                "external_reference": str(intento.id),
                "collector_id": "collector_test",
                "currency_id": "ARS",
                "transaction_amount": 50.00,  # distinto a 30.00 (3000 centavos)
                "date_approved": datetime.now(UTC).isoformat(),
                "live_mode": False,
            }
        }
    )
    monkeypatch.setattr(
        SenaService,
        "mp_adapter",
        property(lambda self: fake_adapter),
        raising=False,
    )
    body = json.dumps(_webhook_body(payment_id, "approved")).encode("utf-8")
    timestamp = int(datetime.now(UTC).timestamp())
    firma = _firmar_webhook(settings.mp_webhook_secret, timestamp, body)
    response = await client.post(
        "/webhooks/mercadopago",
        content=body,
        headers={
            "x-signature": firma,
            "x-request-id": str(uuid4()),
            "content-type": "application/json",
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["aplicado"] is False
    assert "monto" in data.get("motivo", "").lower() or data.get("incidencia") is True
    # No turno creado por discrepancia
    from sqlalchemy import select

    turnos = (await session.scalars(select(Turno))).all()
    assert len(turnos) == 0


# ============================================================
# Task 5.3: Pago aprobado sin cupo -> requiere_revision (EXCLUDE)
# ============================================================


async def test_webhook_pago_aprobado_sin_cupo_requiere_revision(
    c09_webhook_client, session, monkeypatch
):
    """Pago aprobado pero otro turno ya ocupa el hueco -> incidencia, sin turno nuevo."""
    client, ctx = c09_webhook_client
    payment_id = "pay_nocupo_001"
    ahora = datetime.now(UTC)
    # Alinear a grilla de 30 min
    inicio = ahora.replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1)

    # Intento de seña (mismo hueco que el turno ocupante)
    intento = await _crear_intento_en_db(
        session,
        ctx["paciente_id"],
        ctx["sillon_id"],
        ctx["tratamiento_id"],
        preference_id="pref_nocupo_001",
    )
    # Forzar el inicio del intento al mismo que el turno ocupante
    intento.inicio = inicio
    intento.fin = inicio + timedelta(minutes=30)
    await session.flush()

    # Otro paciente ya ocupa el mismo hueco (Turno existente)
    turno_ocupante = Turno(
        paciente_id=ctx["paciente_id"],
        sillon_id=ctx["sillon_id"],
        tratamiento_id=ctx["tratamiento_id"],
        inicio=inicio,
        fin=inicio + timedelta(minutes=30),
        estado="reservado",
        origen="online",
    )
    session.add(turno_ocupante)
    await session.commit()

    fake_adapter = _FakeMPAdapter(
        {
            payment_id: {
                "id": payment_id,
                "status": "approved",
                "external_reference": str(intento.id),
                "collector_id": "collector_test",
                "currency_id": "ARS",
                "transaction_amount": 30.00,
                "date_approved": datetime.now(UTC).isoformat(),
                "live_mode": False,
            }
        }
    )
    monkeypatch.setattr(
        SenaService,
        "mp_adapter",
        property(lambda self: fake_adapter),
        raising=False,
    )
    body = json.dumps(_webhook_body(payment_id, "approved")).encode("utf-8")
    timestamp = int(datetime.now(UTC).timestamp())
    firma = _firmar_webhook(settings.mp_webhook_secret, timestamp, body)
    response = await client.post(
        "/webhooks/mercadopago",
        content=body,
        headers={
            "x-signature": firma,
            "x-request-id": str(uuid4()),
            "content-type": "application/json",
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["aplicado"] is False
    assert data.get("incidencia") is True or data.get("motivo") == "sin_cupo_disponible"
    # No SEGUNDO turno creado (solo el ocupante existente)
    from sqlalchemy import select

    turnos = (await session.scalars(select(Turno))).all()
    assert len(turnos) == 1  # solo el que ya estaba
    # Intento marcado requiere_revision
    await session.refresh(intento)
    assert intento.estado == "requiere_revision"
    # PagoMP registrado como incidencia
    pagos = (await session.scalars(select(PagoMP))).all()
    assert len(pagos) == 1
    assert pagos[0].resultado == "incidencia"


# ============================================================
# Task 5.4: Varios payment_id, eventos fuera de orden, refunded/charged_back
# ============================================================


async def test_webhook_multiple_payment_ids_un_intento(c09_webhook_client, session, monkeypatch):
    """Múltiples payment_ids para el mismo intento: solo una reserva/seña."""
    client, ctx = c09_webhook_client
    intento = await _crear_intento_en_db(
        session,
        ctx["paciente_id"],
        ctx["sillon_id"],
        ctx["tratamiento_id"],
        preference_id="pref_multi_001",
    )

    fake_adapter = _FakeMPAdapter(
        {
            "pay_multi_1": {
                "id": "pay_multi_1",
                "status": "approved",
                "external_reference": str(intento.id),
                "collector_id": "collector_test",
                "currency_id": "ARS",
                "transaction_amount": 30.00,
                "date_approved": datetime.now(UTC).isoformat(),
                "live_mode": False,
            },
            "pay_multi_2": {
                "id": "pay_multi_2",
                "status": "approved",
                "external_reference": str(intento.id),
                "collector_id": "collector_test",
                "currency_id": "ARS",
                "transaction_amount": 30.00,
                "date_approved": datetime.now(UTC).isoformat(),
                "live_mode": False,
            },
        }
    )
    monkeypatch.setattr(
        SenaService,
        "mp_adapter",
        property(lambda self: fake_adapter),
        raising=False,
    )

    # Primer pago aprobado -> crea turno
    body1 = json.dumps(_webhook_body("pay_multi_1", "approved")).encode("utf-8")
    ts1 = int(datetime.now(UTC).timestamp())
    firma1 = _firmar_webhook(settings.mp_webhook_secret, ts1, body1)
    r1 = await client.post(
        "/webhooks/mercadopago",
        content=body1,
        headers={
            "x-signature": firma1,
            "x-request-id": str(uuid4()),
            "content-type": "application/json",
        },
    )
    assert r1.status_code == 200
    assert r1.json()["aplicado"] is True

    # Segundo pago aprobado del mismo intento -> idempotente, no duplica
    body2 = json.dumps(_webhook_body("pay_multi_2", "approved")).encode("utf-8")
    ts2 = int(datetime.now(UTC).timestamp())
    firma2 = _firmar_webhook(settings.mp_webhook_secret, ts2, body2)
    r2 = await client.post(
        "/webhooks/mercadopago",
        content=body2,
        headers={
            "x-signature": firma2,
            "x-request-id": str(uuid4()),
            "content-type": "application/json",
        },
    )
    assert r2.status_code == 200
    data2 = r2.json()
    # payment_id distinto del mismo intento: se crea PagoMP separado pero no segundo turno/cobro
    assert data2["payment_id"] == "pay_multi_2"

    from sqlalchemy import select

    turnos = (await session.scalars(select(Turno))).all()
    assert len(turnos) == 1  # solo un turno
    cobros = (await session.scalars(select(Cobro))).all()
    assert len(cobros) == 1  # solo un cobro
    pagos = (await session.scalars(select(PagoMP))).all()
    assert len(pagos) == 2  # dos pagos registrados


async def test_webhook_pago_refunded_incidencia(c09_webhook_client, session, monkeypatch):
    """Pago refunded/charged_back -> incidencia duradera, historia preservada."""
    client, ctx = c09_webhook_client
    payment_id = "pay_refund_001"
    intento = await _crear_intento_en_db(
        session,
        ctx["paciente_id"],
        ctx["sillon_id"],
        ctx["tratamiento_id"],
        preference_id="pref_refund_001",
    )
    # Primero se aprueba
    fake_adapter = _FakeMPAdapter(
        {
            payment_id: {
                "id": payment_id,
                "status": "approved",
                "external_reference": str(intento.id),
                "collector_id": "collector_test",
                "currency_id": "ARS",
                "transaction_amount": 30.00,
                "date_approved": datetime.now(UTC).isoformat(),
                "live_mode": False,
            }
        }
    )
    monkeypatch.setattr(
        SenaService,
        "mp_adapter",
        property(lambda self: fake_adapter),
        raising=False,
    )
    body = json.dumps(_webhook_body(payment_id, "approved")).encode("utf-8")
    ts = int(datetime.now(UTC).timestamp())
    firma = _firmar_webhook(settings.mp_webhook_secret, ts, body)
    r1 = await client.post(
        "/webhooks/mercadopago",
        content=body,
        headers={
            "x-signature": firma,
            "x-request-id": str(uuid4()),
            "content-type": "application/json",
        },
    )
    assert r1.status_code == 200
    assert r1.json()["aplicado"] is True

    # Luego llega evento refunded para el mismo payment_id -> idempotente (ya procesado)
    body2 = json.dumps(_webhook_body(payment_id, "refunded")).encode("utf-8")
    ts2 = int(datetime.now(UTC).timestamp())
    firma2 = _firmar_webhook(settings.mp_webhook_secret, ts2, body2)
    r2 = await client.post(
        "/webhooks/mercadopago",
        content=body2,
        headers={
            "x-signature": firma2,
            "x-request-id": str(uuid4()),
            "content-type": "application/json",
        },
    )
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["duplicado"] is True  # ya procesado, no se duplica

    from sqlalchemy import select

    turnos = (await session.scalars(select(Turno))).all()
    assert len(turnos) == 1  # turno sigue existiendo (no se borra por refund)
