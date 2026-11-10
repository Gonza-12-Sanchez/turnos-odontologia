"""Contrato C-10 tarea 2.1: GET /catalogo-publico (lectura anónima, solo activos, sin PII ni precio)."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api import deps
from app.main import app
from app.models import Consultorio, Sillon, Tratamiento


@pytest.fixture
async def public_client(engine, session, monkeypatch):
    factory = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(deps, "get_session_factory", lambda: factory)

    consultorio = Consultorio(nombre="Consultorio público")
    session.add(consultorio)
    await session.flush()

    sillon_activo = Sillon(nombre="Sillón A", consultorio_id=consultorio.id)
    sillon_inactivo = Sillon(nombre="Sillón B", consultorio_id=consultorio.id)
    sillon_inactivo.is_active = False
    session.add_all([sillon_activo, sillon_inactivo])

    tratamiento_activo = Tratamiento(
        nombre="Limpieza",
        duracion_min=30,
        precio_referencia_centavos=15000,
        sena_politica="opcional",
        sena_centavos=5000,
    )
    tratamiento_inactivo = Tratamiento(
        nombre="Conducto",
        duracion_min=60,
        precio_referencia_centavos=40000,
        sena_politica="obligatoria",
        sena_centavos=10000,
    )
    tratamiento_inactivo.is_active = False
    session.add_all([tratamiento_activo, tratamiento_inactivo])

    await session.commit()

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="https://test") as client:
        yield client


@pytest.mark.asyncio
async def test_catalogo_publico_solo_activos_y_campos_permitidos(public_client):
    """RED: anónimo recibe 200 con solo activos y campos públicos."""
    response = await public_client.get("/catalogo-publico")
    assert response.status_code == 200, response.text
    data = response.json()

    assert len(data["sillones"]) == 1
    assert data["sillones"][0]["nombre"] == "Sillón A"
    assert "id" in data["sillones"][0]
    assert "nombre" in data["sillones"][0]
    assert "consultorio_id" not in data["sillones"][0]
    assert "is_active" not in data["sillones"][0]
    assert "created_at" not in data["sillones"][0]

    assert len(data["tratamientos"]) == 1
    t = data["tratamientos"][0]
    assert t["nombre"] == "Limpieza"
    assert t["duracion_min"] == 30
    assert t["sena_politica"] == "opcional"
    assert t["sena_centavos"] == 5000
    assert "id" in t
    assert "precio_referencia_centavos" not in t
    assert "is_active" not in t
    assert "created_at" not in t


@pytest.mark.asyncio
async def test_catalogo_publico_lista_vacia_sin_recursos(engine, session, monkeypatch):
    """TRIANGULATE: sin recursos activos devuelve listas vacías."""
    factory = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(deps, "get_session_factory", lambda: factory)

    consultorio = Consultorio(nombre="Consultorio vacío")
    session.add(consultorio)
    await session.flush()

    sillon = Sillon(nombre="Sillón X", consultorio_id=consultorio.id)
    sillon.is_active = False
    tratamiento = Tratamiento(nombre="Tratamiento X", duracion_min=15)
    tratamiento.is_active = False
    session.add_all([sillon, tratamiento])
    await session.commit()

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="https://test") as client:
        response = await client.get("/catalogo-publico")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["sillones"] == []
    assert data["tratamientos"] == []
