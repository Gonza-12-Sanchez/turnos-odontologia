import uuid
import pytest
from app.models import Consultorio, Paciente, Sillon, Tratamiento, Turno, Usuario
from app.services.recordatorio_wa_service import RecordatorioWAService


@pytest.fixture
async def rec_session(session):
    consultorio = Consultorio(nombre="C")
    session.add(consultorio)
    await session.flush()
    sillon = Sillon(nombre="S1", consultorio_id=consultorio.id)
    tratamiento = Tratamiento(nombre="Control", duracion_min=30, precio_referencia_centavos=1000)
    session.add_all([sillon, tratamiento])
    actor = Usuario(email="p@test.com", rol="paciente", password_hash="x", telefono="+54")
    session.add(actor)
    await session.flush()
    pac = Paciente(usuario_id=actor.id, nombre="P", telefono="+54")
    session.add(pac)
    await session.flush()
    from datetime import UTC, datetime, timedelta
    start = datetime(2026, 12, 1, 13, 0, tzinfo=UTC)
    turno = Turno(
        paciente_id=pac.id, sillon_id=sillon.id, tratamiento_id=tratamiento.id,
        inicio=start, fin=start + timedelta(minutes=30), estado="reservado", origen="online",
    )
    session.add(turno)
    await session.commit()
    return session, turno


@pytest.mark.asyncio
async def test_registrar_envio_y_busqueda(rec_session):
    session, turno = rec_session
    svc = RecordatorioWAService(session)
    rec = await svc.registrar_envio(turno.id, "recordatorio_turno", "msg-1", estado="enviado")
    await session.commit()
    assert rec.message_id == "msg-1"
    found = await svc.get_by_message_id("msg-1")
    assert found is not None
    assert found.turno_id == turno.id


@pytest.mark.asyncio
async def test_registrar_respuesta_idempotente(rec_session):
    session, turno = rec_session
    svc = RecordatorioWAService(session)
    await svc.registrar_envio(turno.id, "recordatorio_turno", "msg-2", estado="enviado")
    await session.commit()
    r1 = await svc.registrar_respuesta("msg-2", "confirmo")
    await session.commit()
    assert r1.respuesta == "confirmo"
    assert r1.estado == "respondido"
    # segunda vez no cambia
    r2 = await svc.registrar_respuesta("msg-2", "cancelo")
    assert r2.respuesta == "confirmo"


@pytest.mark.asyncio
async def test_get_by_turno_id(rec_session):
    session, turno = rec_session
    svc = RecordatorioWAService(session)
    await svc.registrar_envio(turno.id, "recordatorio_turno", "msg-3", estado="enviado")
    await session.commit()
    lst = await svc.get_by_turno_id(turno.id)
    assert len(lst) == 1
