"""C-07 acciones permitidas."""

from datetime import UTC, datetime, timedelta

import pytest

from app.services.agenda_lectura_service import AgendaLecturaService


class DummyTurno:
    def __init__(self, estado, inicio, sillon, tratamiento):
        self.id = __import__("uuid").uuid4()
        self.estado = estado
        self.inicio = inicio
        self.sillon_id = sillon.id
        self.sillon = sillon
        self.tratamiento_id = tratamiento.id
        self.tratamiento = tratamiento
        self.paciente_id = __import__("uuid").uuid4()
        self.paciente = type("P", (), {"nombre": "P"})()
        self.origen = "online"
        self.es_sobreturno = False
        self.motivo_sobreturno = None
        self.fin = inicio + timedelta(minutes=30)


@pytest.mark.asyncio
async def test_acciones_lejano_permite_cancelar(monkeypatch):
    import app.services.agenda_lectura_service as svc

    monkeypatch.setattr(svc.settings, "appointment_cancel_minutes", 120)

    # monkeypatch repo
    class Repo:
        def __init__(self, session):
            pass

        async def list_for_paciente(self, *a, **k):
            sillon = type("S", (), {"id": __import__("uuid").uuid4(), "nombre": "S1"})()
            trat = type(
                "T", (), {"id": __import__("uuid").uuid4(), "nombre": "C", "duracion_min": 30}
            )()
            return [DummyTurno("reservado", datetime.now(UTC) + timedelta(hours=3), sillon, trat)]

    monkeypatch.setattr(svc, "AgendaLecturaRepository", Repo)
    service = AgendaLecturaService(session=None)
    res = await service.mis_reservas(paciente=None)
    assert res[0].acciones.cancelar is True
    assert res[0].acciones.confirmar is True


@pytest.mark.asyncio
async def test_acciones_cercano_no_cancelar(monkeypatch):
    import app.services.agenda_lectura_service as svc

    monkeypatch.setattr(svc.settings, "appointment_cancel_minutes", 120)

    class Repo:
        def __init__(self, session):
            pass

        async def list_for_paciente(self, *a, **k):
            sillon = type("S", (), {"id": __import__("uuid").uuid4(), "nombre": "S1"})()
            trat = type(
                "T", (), {"id": __import__("uuid").uuid4(), "nombre": "C", "duracion_min": 30}
            )()
            return [
                DummyTurno("reservado", datetime.now(UTC) + timedelta(minutes=30), sillon, trat)
            ]

    monkeypatch.setattr(svc, "AgendaLecturaRepository", Repo)
    service = AgendaLecturaService(session=None)
    res = await service.mis_reservas(paciente=None)
    assert res[0].acciones.cancelar is False
    assert res[0].acciones.confirmar is True
