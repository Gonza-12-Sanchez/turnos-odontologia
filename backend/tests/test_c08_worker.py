import pytest
from app.workers.whatsapp_worker import process_one


@pytest.mark.asyncio
async def test_process_one_turno_inexistente(session):
    # turno id random -> returns True (discarded)
    import uuid
    ok = await process_one(str(uuid.uuid4()), session)
    assert ok is True


@pytest.mark.asyncio
async def test_process_one_envio_exitoso(session, monkeypatch):
    # need a turno; build minimal
    from app.models import Consultorio, Paciente, Sillon, Tratamiento, Turno, Usuario
    from datetime import UTC, datetime, timedelta
    consultorio = Consultorio(nombre="C")
    session.add(consultorio)
    await session.flush()
    sillon = Sillon(nombre="S1", consultorio_id=consultorio.id)
    tratamiento = Tratamiento(nombre="Control", duracion_min=30, precio_referencia_centavos=1000)
    session.add_all([sillon, tratamiento])
    actor = Usuario(email="p@w.com", rol="paciente", password_hash="x", telefono="+54")
    session.add(actor)
    await session.flush()
    pac = Paciente(usuario_id=actor.id, nombre="P", telefono="+54")
    session.add(pac)
    await session.flush()
    start = datetime(2026, 12, 1, 13, 0, tzinfo=UTC)
    turno = Turno(
        paciente_id=pac.id, sillon_id=sillon.id, tratamiento_id=tratamiento.id,
        inicio=start, fin=start + timedelta(minutes=30), estado="reservado", origen="online",
    )
    session.add(turno)
    await session.commit()

    ok = await process_one(str(turno.id), session)
    assert ok is True
