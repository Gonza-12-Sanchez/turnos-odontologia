"""C-07 schemas de lectura."""

from datetime import UTC, datetime
from uuid import uuid4

from app.schemas.turnos import AccionesOut, AgendaSillonOut, AgendaTurnoOut, MisReservaOut


def test_acciones_out():
    a = AccionesOut(cancelar=True, confirmar=False, reprogramar=True)
    assert a.cancelar is True
    assert a.reprogramar is True


def test_agenda_turno_out_serialization():
    now = datetime(2026, 12, 1, 13, 0, tzinfo=UTC)
    obj = AgendaTurnoOut(
        id=uuid4(),
        sillon_id=uuid4(),
        sillon_nombre="S1",
        paciente_id=uuid4(),
        paciente_nombre="P",
        tratamiento_id=uuid4(),
        tratamiento_nombre="Control",
        duracion_min=30,
        inicio=now,
        fin=now,
        estado="reservado",
        origen="online",
        tolerancia_min=5,
    )
    data = obj.model_dump()
    assert data["tolerancia_min"] == 5
    assert data["sillon_nombre"] == "S1"


def test_mis_reserva_out_acciones():
    now = datetime(2026, 12, 1, 13, 0, tzinfo=UTC)
    obj = MisReservaOut(
        id=uuid4(),
        sillon_id=uuid4(),
        sillon_nombre="S1",
        tratamiento_id=uuid4(),
        tratamiento_nombre="Control",
        inicio=now,
        fin=now,
        estado="reservado",
        origen="online",
        acciones=AccionesOut(cancelar=True, confirmar=True, reprogramar=True),
    )
    assert obj.acciones.cancelar is True
    assert obj.acciones_permitidas is None or obj.acciones_permitidas.cancelar is True


def test_agenda_sillon_out():
    g = AgendaSillonOut(sillon_id=uuid4(), sillon_nombre="S1", sillon={"id": uuid4(), "nombre": "S1"}, turnos=[])
    assert g.turnos == []
