"""C-07 repositorio de lectura."""

from datetime import UTC, date, datetime, timedelta

import pytest

from app.models import Consultorio, Paciente, Sillon, Tratamiento, Turno, Usuario
from app.repositories.agenda_lectura_repository import AgendaLecturaRepository


@pytest.fixture
async def repo_data(session):
    consultorio = Consultorio(nombre="C")
    session.add(consultorio)
    await session.flush()
    sillones = [Sillon(nombre=f"S{i}", consultorio_id=consultorio.id) for i in (1, 2)]
    tratamiento = Tratamiento(nombre="Control", duracion_min=30, precio_referencia_centavos=1000)
    session.add_all([*sillones, tratamiento])
    user = Usuario(email="p@x.com", rol="paciente", password_hash="x", telefono="+54")
    session.add(user)
    await session.flush()
    pac = Paciente(usuario_id=user.id, nombre="Paciente", telefono="+54")
    session.add(pac)
    await session.flush()
    start = datetime(2026, 12, 1, 13, 0, tzinfo=UTC)
    t1 = Turno(
        paciente_id=pac.id,
        sillon_id=sillones[0].id,
        tratamiento_id=tratamiento.id,
        inicio=start,
        fin=start + timedelta(minutes=30),
        estado="reservado",
        origen="online",
    )
    t2 = Turno(
        paciente_id=pac.id,
        sillon_id=sillones[1].id,
        tratamiento_id=tratamiento.id,
        inicio=start + timedelta(hours=1),
        fin=start + timedelta(hours=1, minutes=30),
        estado="confirmado",
        origen="online",
    )
    session.add_all([t1, t2])
    await session.commit()
    return {"sillones": sillones, "paciente": pac, "turnos": [t1, t2], "tratamiento": tratamiento}


@pytest.mark.asyncio
async def test_list_for_agenda_filters(session, repo_data):
    repo = AgendaLecturaRepository(session)
    res = await repo.list_for_agenda(date(2026, 12, 1), sillon_id=repo_data["sillones"][0].id)
    assert len(res) == 1
    assert res[0].paciente.nombre == "Paciente"
    assert res[0].tratamiento.nombre == "Control"
    assert res[0].sillon.nombre.startswith("S")


@pytest.mark.asyncio
async def test_list_for_paciente_filters(session, repo_data):
    repo = AgendaLecturaRepository(session)
    pac = repo_data["paciente"]
    res = await repo.list_for_paciente(pac.id, estado="confirmado")
    assert len(res) == 1
    assert res[0].estado == "confirmado"
    # eager loaded
    assert res[0].sillon is not None
