"""C-07 performance smoke."""

import time
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api import deps
from app.db import redis as redis_client
from app.main import app
from app.models import Consultorio, Paciente, Sillon, Tratamiento, Turno, Usuario
from app.shared.security import create_access_token


@pytest.mark.asyncio
async def test_perf_agenda_multi_sillon(engine, session, real_redis, monkeypatch):
    factory = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(deps, "get_session_factory", lambda: factory)
    monkeypatch.setattr(redis_client, "get_redis", lambda: real_redis)

    consultorio = Consultorio(nombre="C")
    session.add(consultorio)
    await session.flush()
    sillones = [Sillon(nombre=f"S{i}", consultorio_id=consultorio.id) for i in (1, 2)]
    tratamiento = Tratamiento(nombre="Control", duracion_min=30, precio_referencia_centavos=1000)
    session.add_all([*sillones, tratamiento])
    user = Usuario(
        email="odo.perf@example.com", rol="odontologo", password_hash="x", telefono="+54"
    )
    session.add(user)
    await session.flush()
    token = create_access_token(user.id, ["odontologo"], user.email)[0]

    pac_user = Usuario(
        email="pac.perf@example.com", rol="paciente", password_hash="x", telefono="+54"
    )
    session.add(pac_user)
    await session.flush()
    pac = Paciente(usuario_id=pac_user.id, nombre="P", telefono="+54")
    session.add(pac)
    await session.flush()

    start = datetime(2026, 12, 1, 8, 0, tzinfo=UTC)
    turnos = []
    for i in range(16):
        sillon = sillones[i % 2]
        t0 = start + timedelta(minutes=30 * i)
        turnos.append(
            Turno(
                paciente_id=pac.id,
                sillon_id=sillon.id,
                tratamiento_id=tratamiento.id,
                inicio=t0,
                fin=t0 + timedelta(minutes=30),
                estado="reservado",
                origen="online",
            )
        )
    session.add_all(turnos)
    await session.commit()

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(
        transport=transport, base_url="https://test", headers={"Authorization": f"Bearer {token}"}
    ) as client:
        t0 = time.perf_counter()
        response = await client.get("/agenda?fecha=2026-12-01")
        elapsed = time.perf_counter() - t0
        assert response.status_code == 200
        assert elapsed < 1.0
