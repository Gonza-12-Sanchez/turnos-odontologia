"""C-09: intento de seña, pagos MP e idempotencia (tareas 2.2, 4.x, 5.x)."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import (
    AuditoriaCobro,
    Consultorio,
    IdempotenciaSolicitud,
    IntentoSena,
    Paciente,
    PagoMP,
    Sillon,
    Tratamiento,
    Usuario,
)


@pytest.fixture
async def c09_seeds(session):
    consultorio = Consultorio(nombre="Consultorio C09S")
    session.add(consultorio)
    await session.flush()
    sillon = Sillon(consultorio_id=consultorio.id, nombre="Sillon C09S", is_active=True)
    session.add(sillon)
    tratamiento = Tratamiento(
        nombre="Limpieza", duracion_min=30,
        precio_referencia_centavos=10000,
        sena_politica="obligatoria", sena_centavos=3000,
    )
    session.add(tratamiento)
    await session.flush()
    usuario = Usuario(email="pac.c09s@example.com", rol="paciente", password_hash="ficticio")
    session.add(usuario)
    await session.flush()
    paciente = Paciente(usuario_id=usuario.id, nombre="Paciente C09S", telefono="1112345678")
    session.add(paciente)
    await session.flush()
    await session.commit()
    return {
        "sillon_id": sillon.id,
        "tratamiento_id": tratamiento.id,
        "paciente_id": paciente.id,
        "usuario_id": usuario.id,
    }


async def test_intento_sena_persiste(session, c09_seeds):
    seeds = c09_seeds
    ahora = datetime.now(UTC)
    intento = IntentoSena(
        paciente_id=seeds["paciente_id"],
        sillon_id=seeds["sillon_id"],
        tratamiento_id=seeds["tratamiento_id"],
        inicio=ahora + timedelta(hours=1),
        fin=ahora + timedelta(hours=1, minutes=30),
        duracion_min=30,
        monto_centavos=3000,
        moneda="ARS",
        sena_politica="obligatoria",
        estado="creando_checkout",
        preference_id="pref_123",
        expires_at=ahora + timedelta(minutes=15),
        modo="mock",
    )
    session.add(intento)
    await session.flush()
    await session.refresh(intento)
    assert intento.id is not None
    assert intento.estado == "creando_checkout"
    assert intento.turno_id is None
    # recuperar
    got = await session.get(IntentoSena, intento.id)
    assert got is not None
    assert got.preference_id == "pref_123"


async def test_intento_estado_valido_restringido(session, c09_seeds):
    seeds = c09_seeds
    ahora = datetime.now(UTC)
    intento = IntentoSena(
        paciente_id=seeds["paciente_id"],
        sillon_id=seeds["sillon_id"],
        tratamiento_id=seeds["tratamiento_id"],
        inicio=ahora + timedelta(hours=1),
        fin=ahora + timedelta(hours=1, minutes=30),
        duracion_min=30,
        monto_centavos=3000,
        moneda="ARS",
        sena_politica="obligatoria",
        estado="pendiente",
        expires_at=ahora + timedelta(minutes=15),
        modo="mock",
    )
    session.add(intento)
    await session.flush()
    await session.refresh(intento)
    assert intento.estado == "pendiente"


async def test_pago_mp_payment_id_unico(session, c09_seeds):
    seeds = c09_seeds
    ahora = datetime.now(UTC)
    intento = IntentoSena(
        paciente_id=seeds["paciente_id"],
        sillon_id=seeds["sillon_id"],
        tratamiento_id=seeds["tratamiento_id"],
        inicio=ahora + timedelta(hours=1),
        fin=ahora + timedelta(hours=1, minutes=30),
        duracion_min=30,
        monto_centavos=3000,
        moneda="ARS",
        sena_politica="obligatoria",
        estado="pendiente",
        expires_at=ahora + timedelta(minutes=15),
        modo="mock",
    )
    session.add(intento)
    await session.flush()
    pago = PagoMP(
        intento_id=intento.id,
        payment_id="pay_unique_1",
        estado_proveedor="approved",
        monto_centavos=3000,
        moneda="ARS",
        receptor_id="collector_1",
        modo="mock",
        resultado="aplicado",
    )
    session.add(pago)
    await session.flush()
    await session.refresh(pago)
    assert pago.id is not None
    # duplicar payment_id falla
    dup = PagoMP(
        intento_id=intento.id,
        payment_id="pay_unique_1",
        estado_proveedor="approved",
        monto_centavos=3000,
        moneda="ARS",
        receptor_id="collector_1",
        modo="mock",
        resultado="aplicado",
    )
    session.add(dup)
    with pytest.raises(IntegrityError):
        await session.flush()
    await session.rollback()


async def test_idempotencia_solicitud_unique(session, c09_seeds):
    seeds = c09_seeds
    ide = IdempotenciaSolicitud(
        usuario_id=seeds["usuario_id"],
        operacion="pagos:sena",
        clave="clave_abc",
        huella="huella_xyz",
        resultado=None,
    )
    session.add(ide)
    await session.flush()
    await session.refresh(ide)
    assert ide.id is not None
    dup = IdempotenciaSolicitud(
        usuario_id=seeds["paciente_id"],
        operacion="pagos:sena",
        clave="clave_abc",
        huella="otra_huella",
        resultado=None,
    )
    session.add(dup)
    with pytest.raises(IntegrityError):
        await session.flush()
    await session.rollback()


async def test_auditoria_cobro_persiste(session, c09_seeds):
    seeds = c09_seeds
    auditoria = AuditoriaCobro(
        actor_id=seeds["usuario_id"],
        accion="registrar_cobro",
        centavos=7000,
        motivo="Cobro en mostrador",
    )
    session.add(auditoria)
    await session.flush()
    await session.refresh(auditoria)
    assert auditoria.id is not None
    assert auditoria.created_at.tzinfo is not None
