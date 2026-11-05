"""Tests de invariantes y escenarios del spec core/models (C-02)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models import (
    Cobro,
    Consultorio,
    Paciente,
    Sillon,
    Tratamiento,
    Turno,
    Usuario,
)
from app.repositories.base_repository import BaseRepository
from app.repositories.unit_of_work import UnitOfWork
from app.schemas.phone import validate_ar_phone


async def _make_base(session):
    consultorio = Consultorio(nombre="Consultorio test")
    session.add(consultorio)
    await session.flush()
    sillon = Sillon(consultorio_id=consultorio.id, nombre="Sillon 1")
    session.add(sillon)
    await session.flush()
    tratamiento = Tratamiento(nombre="Limpieza", duracion_min=30, precio_referencia_centavos=500000)
    session.add(tratamiento)
    await session.flush()
    usuario = Usuario(email="paciente@test.example", password_hash="x", rol="paciente")
    session.add(usuario)
    await session.flush()
    paciente = Paciente(
        usuario_id=usuario.id, nombre="Paciente Test", telefono="+54 9 11 0000-0000"
    )
    session.add(paciente)
    await session.flush()
    return sillon, tratamiento, paciente


@pytest.mark.asyncio
async def test_turno_valido_persiste(session):
    sillon, tratamiento, paciente = await _make_base(session)
    inicio = datetime.now(UTC).replace(microsecond=0) + timedelta(days=1)
    fin = inicio + timedelta(minutes=tratamiento.duracion_min)
    turno = Turno(
        paciente_id=paciente.id,
        sillon_id=sillon.id,
        tratamiento_id=tratamiento.id,
        inicio=inicio,
        fin=fin,
    )
    session.add(turno)
    await session.commit()
    assert turno.id is not None
    assert turno.fin == inicio + timedelta(minutes=30)


@pytest.mark.asyncio
async def test_turno_solapado_rechazado(session):
    sillon, tratamiento, paciente = await _make_base(session)
    inicio = datetime.now(UTC).replace(microsecond=0) + timedelta(days=1)
    fin = inicio + timedelta(minutes=30)
    t1 = Turno(
        paciente_id=paciente.id,
        sillon_id=sillon.id,
        tratamiento_id=tratamiento.id,
        inicio=inicio,
        fin=fin,
    )
    session.add(t1)
    await session.commit()

    t2 = Turno(
        paciente_id=paciente.id,
        sillon_id=sillon.id,
        tratamiento_id=tratamiento.id,
        inicio=inicio + timedelta(minutes=10),
        fin=inicio + timedelta(minutes=40),
    )
    session.add(t2)
    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


@pytest.mark.asyncio
async def test_cancelado_no_bloquea(session):
    sillon, tratamiento, paciente = await _make_base(session)
    inicio = datetime.now(UTC).replace(microsecond=0) + timedelta(days=2)
    fin = inicio + timedelta(minutes=30)
    t1 = Turno(
        paciente_id=paciente.id,
        sillon_id=sillon.id,
        tratamiento_id=tratamiento.id,
        inicio=inicio,
        fin=fin,
        estado="cancelado",
    )
    session.add(t1)
    await session.commit()

    t2 = Turno(
        paciente_id=paciente.id,
        sillon_id=sillon.id,
        tratamiento_id=tratamiento.id,
        inicio=inicio,
        fin=fin,
    )
    session.add(t2)
    await session.commit()  # no debe lanzar


@pytest.mark.asyncio
async def test_softdeleted_no_bloquea(session):
    sillon, tratamiento, paciente = await _make_base(session)
    inicio = datetime.now(UTC).replace(microsecond=0) + timedelta(days=3)
    fin = inicio + timedelta(minutes=30)
    t1 = Turno(
        paciente_id=paciente.id,
        sillon_id=sillon.id,
        tratamiento_id=tratamiento.id,
        inicio=inicio,
        fin=fin,
    )
    session.add(t1)
    await session.commit()
    t1.is_active = False
    await session.commit()

    t2 = Turno(
        paciente_id=paciente.id,
        sillon_id=sillon.id,
        tratamiento_id=tratamiento.id,
        inicio=inicio,
        fin=fin,
    )
    session.add(t2)
    await session.commit()


@pytest.mark.asyncio
async def test_sillones_distintos_no_bloquean(session):
    sillon, tratamiento, paciente = await _make_base(session)
    consultorio = (await session.execute(select(Consultorio))).scalars().first()
    sillon2 = Sillon(consultorio_id=consultorio.id, nombre="Sillon 2")
    session.add(sillon2)
    await session.flush()

    inicio = datetime.now(UTC).replace(microsecond=0) + timedelta(days=4)
    fin = inicio + timedelta(minutes=30)
    t1 = Turno(
        paciente_id=paciente.id,
        sillon_id=sillon.id,
        tratamiento_id=tratamiento.id,
        inicio=inicio,
        fin=fin,
    )
    session.add(t1)
    await session.commit()

    t2 = Turno(
        paciente_id=paciente.id,
        sillon_id=sillon2.id,
        tratamiento_id=tratamiento.id,
        inicio=inicio,
        fin=fin,
    )
    session.add(t2)
    await session.commit()


@pytest.mark.asyncio
async def test_turnos_adyacentes_no_solapan(session):
    sillon, tratamiento, paciente = await _make_base(session)
    inicio = datetime.now(UTC).replace(microsecond=0) + timedelta(days=5)
    fin = inicio + timedelta(minutes=30)
    t1 = Turno(
        paciente_id=paciente.id,
        sillon_id=sillon.id,
        tratamiento_id=tratamiento.id,
        inicio=inicio,
        fin=fin,
    )
    session.add(t1)
    await session.commit()

    inicio2 = fin
    fin2 = inicio2 + timedelta(minutes=30)
    t2 = Turno(
        paciente_id=paciente.id,
        sillon_id=sillon.id,
        tratamiento_id=tratamiento.id,
        inicio=inicio2,
        fin=fin2,
    )
    session.add(t2)
    await session.commit()


@pytest.mark.asyncio
async def test_timestamps_tz(session):
    sillon, tratamiento, paciente = await _make_base(session)
    inicio = datetime.now(UTC).replace(microsecond=0) + timedelta(days=6)
    fin = inicio + timedelta(minutes=30)
    turno = Turno(
        paciente_id=paciente.id,
        sillon_id=sillon.id,
        tratamiento_id=tratamiento.id,
        inicio=inicio,
        fin=fin,
    )
    session.add(turno)
    await session.commit()
    await session.refresh(turno)
    assert turno.inicio.tzinfo is not None
    assert turno.fin.tzinfo is not None
    assert turno.created_at.tzinfo is not None


@pytest.mark.asyncio
async def test_naive_rechazado(session):
    sillon, tratamiento, paciente = await _make_base(session)
    naive = datetime.now().replace(microsecond=0) + timedelta(days=7)
    turno = Turno(
        paciente_id=paciente.id,
        sillon_id=sillon.id,
        tratamiento_id=tratamiento.id,
        inicio=naive,
        fin=naive + timedelta(minutes=30),
    )
    session.add(turno)
    try:
        await session.commit()
        # Si no lanza, el test falla: se esperaba rechazo
        pytest.fail("Se esperaba rechazo de datetime naive")
    except (ValueError, TypeError, SQLAlchemyError):
        await session.rollback()


@pytest.mark.asyncio
async def test_centavos(session):
    tratamiento = Tratamiento(nombre="T2", duracion_min=10, precio_referencia_centavos=123)
    session.add(tratamiento)
    await session.commit()
    await session.refresh(tratamiento)
    assert tratamiento.precio_referencia_centavos == 123
    assert isinstance(tratamiento.precio_referencia_centavos, int)

    # Cobro necesita turno
    consultorio = Consultorio(nombre="C2")
    session.add(consultorio)
    await session.flush()
    sillon = Sillon(consultorio_id=consultorio.id, nombre="S2")
    session.add(sillon)
    await session.flush()
    usuario = Usuario(email="p2@test.example", password_hash="x", rol="paciente")
    session.add(usuario)
    await session.flush()
    paciente = Paciente(usuario_id=usuario.id, nombre="P2", telefono="+54 9 11 0000-0000")
    session.add(paciente)
    await session.flush()
    inicio = datetime.now(UTC).replace(microsecond=0) + timedelta(days=8)
    turno = Turno(
        paciente_id=paciente.id,
        sillon_id=sillon.id,
        tratamiento_id=tratamiento.id,
        inicio=inicio,
        fin=inicio + timedelta(minutes=10),
    )
    session.add(turno)
    await session.commit()
    cobro = Cobro(turno_id=turno.id, monto_centavos=500000, medio="efectivo", tipo="total")
    session.add(cobro)
    await session.commit()
    await session.refresh(cobro)
    assert cobro.monto_centavos == 500000
    assert isinstance(cobro.monto_centavos, int)


@pytest.mark.asyncio
async def test_soft_delete(session):
    consultorio = Consultorio(nombre="Soft")
    session.add(consultorio)
    await session.commit()
    repo = BaseRepository(session, Consultorio)
    await repo.soft_delete(consultorio)
    await session.commit()
    assert consultorio.is_active is False
    assert consultorio.deleted_at is not None
    res = await session.execute(select(Consultorio).where(Consultorio.id == consultorio.id))
    assert res.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_uow_commit_rollback(engine, session):
    factory = async_sessionmaker(engine, expire_on_commit=False)
    # commit persiste
    async with UnitOfWork(factory) as uow:
        c = Consultorio(nombre="UoW-commit")
        await BaseRepository(uow.session, Consultorio).add(c)
        await uow.commit()
    async with factory() as s:
        res = await s.execute(select(Consultorio).where(Consultorio.nombre == "UoW-commit"))
        assert res.scalar_one_or_none() is not None

    # excepción hace rollback
    try:
        async with UnitOfWork(factory) as uow:
            c = Consultorio(nombre="UoW-rollback")
            await BaseRepository(uow.session, Consultorio).add(c)
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    async with factory() as s:
        res = await s.execute(select(Consultorio).where(Consultorio.nombre == "UoW-rollback"))
        assert res.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_phone_ar():
    assert validate_ar_phone("+54 9 11 00000000") == "+54 9 11 00000000"
    with pytest.raises(ValueError):
        validate_ar_phone("12345")


@pytest.mark.asyncio
async def test_seed_idempotente(session):
    from app.db.seed import seed_demo

    factory = async_sessionmaker(session.bind, expire_on_commit=False)
    async with factory() as s:
        await seed_demo(s)
    async with factory() as s:
        from sqlalchemy import func

        c1 = (await s.execute(select(func.count()).select_from(Consultorio))).scalar()
        u1 = (await s.execute(select(func.count()).select_from(Usuario))).scalar()
        t1 = (await s.execute(select(func.count()).select_from(Tratamiento))).scalar()
        p1 = (await s.execute(select(func.count()).select_from(Paciente))).scalar()
    # re-run
    async with factory() as s:
        await seed_demo(s)
    async with factory() as s:
        c2 = (await s.execute(select(func.count()).select_from(Consultorio))).scalar()
        u2 = (await s.execute(select(func.count()).select_from(Usuario))).scalar()
        t2 = (await s.execute(select(func.count()).select_from(Tratamiento))).scalar()
        p2 = (await s.execute(select(func.count()).select_from(Paciente))).scalar()
    assert (c1, u1, t1, p1) == (c2, u2, t2, p2)
    # counts expected at least
    assert c1 >= 1 and u1 >= 3 and t1 >= 3 and p1 >= 1
