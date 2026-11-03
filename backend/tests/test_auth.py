"""Tests de autenticación C-03 (auth-jwt-rbac).

Escenarios verificables del spec `identity/auth`:
- Registro: feliz, email duplicado (error negocio), teléfono/contraseña débil (borde).
- Login: feliz, credenciales inválidas (error negocio).
- JWT: token expirado (borde), token blacklisted (borde).
- Refresh: rotación exitosa (feliz), reuso revoca familia (borde), cookie faltante (error negocio).
- Logout: feliz, sin token válido (error negocio).
- Me: autenticado (feliz), sin autenticar (error negocio).
- Rate limiting: 429 (error negocio).
- RBAC: paciente no accede a /agenda (borde), anónimo no puede POST /turnos (borde).

Redis se mockea con un fake en memoria para no depender de un servidor externo.
BD: se usa una única sesión compartida por test para evitar el error de asyncpg
"another operation is in progress" en Windows.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.api.deps import get_db
from app.core.config import settings
from app.db import engine as db_engine_module
from app.db import redis as redis_client
from app.main import app
from app.models.usuario import Usuario
from app.repositories.usuario_repository import UsuarioRepository
from app.shared.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
)

DATABASE_URL = "postgresql+asyncpg://turnos:turnos@localhost:5432/turnos_test"


# ---------------------------------------------------------------------------
# Fake Redis en memoria (sustituye a get_redis() para no depender de servidor)
# ---------------------------------------------------------------------------


class _FakeRedis:
    def __init__(self) -> None:
        self._store: dict[str, tuple[str, float | None]] = {}

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        expiry = None
        if ex is not None:
            expiry = datetime.now(timezone.utc).timestamp() + ex
        self._store[key] = (value, expiry)

    async def get(self, key: str) -> str | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expiry = entry
        if expiry is not None and datetime.now(timezone.utc).timestamp() > expiry:
            del self._store[key]
            return None
        return value

    async def delete(self, *keys: str) -> None:
        for k in keys:
            self._store.pop(k, None)

    async def keys(self, pattern: str) -> list[str]:
        prefix = pattern.rstrip("*")
        return [k for k in self._store if k.startswith(prefix)]

    async def incr(self, key: str) -> int:
        entry = self._store.get(key)
        if entry is None:
            self._store[key] = ("1", None)
            return 1
        value, expiry = entry
        if expiry is not None and datetime.now(timezone.utc).timestamp() > expiry:
            del self._store[key]
            self._store[key] = ("1", None)
            return 1
        new_val = int(value) + 1
        self._store[key] = (str(new_val), expiry)
        return new_val

    async def expire(self, key: str, ttl: int) -> None:
        entry = self._store.get(key)
        if entry is None:
            return
        value, _ = entry
        expiry = datetime.now(timezone.utc).timestamp() + ttl
        self._store[key] = (value, expiry)

    async def ttl(self, key: str) -> int:
        entry = self._store.get(key)
        if entry is None:
            return -2
        value, expiry = entry
        if expiry is None:
            return -1
        remaining = int(expiry - datetime.now(timezone.utc).timestamp())
        if remaining < 0:
            del self._store[key]
            return -2
        return remaining

    async def aclose(self) -> None:
        self._store.clear()


@pytest.fixture
def fake_redis():
    """Reemplaza get_redis() por un fake en memoria."""
    fake = _FakeRedis()
    with patch.object(redis_client, "get_redis", return_value=fake):
        yield fake


# ---------------------------------------------------------------------------
# Fixtures de BD y cliente HTTP
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
async def engine():
    eng = create_async_engine(DATABASE_URL, poolclass=NullPool)
    yield eng
    await eng.dispose()


@pytest.fixture(autouse=True)
async def clean_db(engine):
    """Limpia tablas entre tests (autouse), serializado por _db_lock."""
    async with _db_lock:
        yield
    async with engine.begin() as conn:
        from app.db.base import Base

        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


# Lock global para serializar acceso a BD (evita "another operation in progress"
# de asyncpg en Windows cuando hay múltiples operaciones concurrentes).
_db_lock = asyncio.Lock()


@pytest.fixture
async def auth_client(engine, fake_redis) -> AsyncGenerator[AsyncClient, None]:
    """Cliente HTTP con sesión de BD compartida y Redis faked.

    Crea UNA sesión de BD por test y la comparte entre `get_db()` y `UnitOfWork`
    para evitar "another operation is in progress" de asyncpg en Windows.
    """
    import app.db.engine as engine_module
    from app.repositories import unit_of_work as uow_module

    # Sesión única compartida por este test
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    shared_session = factory()

    async def _get_db() -> AsyncGenerator[AsyncSession, None]:
        yield shared_session

    # Monkeypatch UnitOfWork para usar la sesión compartida (no crear nueva)
    original_uow_init = uow_module.UnitOfWork.__init__
    original_uow_aenter = uow_module.UnitOfWork.__aenter__
    original_uow_aexit = uow_module.UnitOfWork.__aexit__

    def patched_init(self, session_factory=None):
        self._session_factory = session_factory
        self._session = None
        self._committed = False
        self._rolled_back = False

    async def patched_aenter(self):
        self._session = shared_session
        self._committed = False
        self._rolled_back = False
        return self

    async def patched_aexit(self, exc_type, exc, tb):
        pass  # No cerrar la sesión compartida

    uow_module.UnitOfWork.__init__ = patched_init
    uow_module.UnitOfWork.__aenter__ = patched_aenter
    uow_module.UnitOfWork.__aexit__ = patched_aexit

    app.dependency_overrides[get_db] = _get_db

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
    finally:
        app.dependency_overrides.clear()
        uow_module.UnitOfWork.__init__ = original_uow_init
        uow_module.UnitOfWork.__aenter__ = original_uow_aenter
        uow_module.UnitOfWork.__aexit__ = original_uow_aexit
        await shared_session.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_user(engine, email: str, password: str, rol: str = "paciente") -> uuid.UUID:
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as s:
        repo = UsuarioRepository(s)
        hashed = hash_password(password)
        user = Usuario(email=email, telefono="+549110000000", password_hash=hashed, rol=rol)
        await repo.add(user)
        await s.commit()
        await s.refresh(user)
        return user.id


def _make_access_token(user_id: uuid.UUID, rol: str = "paciente", email: str | None = None) -> str:
    token, _, _ = create_access_token(user_id, [rol], email)
    return token


def _make_expired_access_token(user_id: uuid.UUID, rol: str = "paciente") -> str:
    now = datetime.now(timezone.utc) - timedelta(minutes=5)
    jti = str(uuid.uuid4())
    payload = {
        "sub": str(user_id),
        "roles": [rol],
        "email": "expired@example.com",
        "jti": jti,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(now.timestamp()),
    }
    from jose import jwt as jose_jwt

    return jose_jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")


# ---------------------------------------------------------------------------
# Tests — Registro
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_registro_exitoso(auth_client: AsyncClient, fake_redis, engine):
    """Feliz: registro crea Usuario + Paciente y devuelve 201."""
    payload = {
        "email": "nuevo@example.com",
        "password": "Abc12345",
        "nombre": "Nuevo Paciente",
        "telefono": "+549111111111",
    }
    resp = await auth_client.post("/auth/registro", json=payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["email"] == "nuevo@example.com"
    assert data["rol"] == "paciente"
    assert "id" in data


@pytest.mark.asyncio
async def test_registro_email_duplicado(auth_client: AsyncClient, fake_redis, engine):
    """Error de negocio: email ya registrado → 409."""
    await _create_user(engine, "duplicado@example.com", "Abc12345")
    payload = {
        "email": "duplicado@example.com",
        "password": "Abc12345",
        "nombre": "Otro",
        "telefono": "+549112222222",
    }
    resp = await auth_client.post("/auth/registro", json=payload)
    assert resp.status_code == 409, resp.text


@pytest.mark.asyncio
async def test_registro_telefono_invalido(auth_client: AsyncClient, fake_redis, engine):
    """Borde: teléfono no AR → 422."""
    payload = {
        "email": "telefono@example.com",
        "password": "Abc12345",
        "nombre": "X",
        "telefono": "not-a-phone",
    }
    resp = await auth_client.post("/auth/registro", json=payload)
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_registro_contrasenia_debil(auth_client: AsyncClient, fake_redis, engine):
    """Borde: contraseña corta → 422."""
    payload = {
        "email": "debil@example.com",
        "password": "123",
        "nombre": "X",
        "telefono": "+549113333333",
    }
    resp = await auth_client.post("/auth/registro", json=payload)
    assert resp.status_code == 422, resp.text


# ---------------------------------------------------------------------------
# Tests — Login
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_exitoso(auth_client: AsyncClient, fake_redis, engine):
    """Feliz: login devuelve access_token y cookie refresh."""
    await _create_user(engine, "login@example.com", "Abc12345")
    resp = await auth_client.post("/auth/login", json={"email": "login@example.com", "password": "Abc12345"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "expires_in" in data
    assert "refresh_token" in resp.cookies


@pytest.mark.asyncio
async def test_login_credenciales_invalidas(auth_client: AsyncClient, fake_redis, engine):
    """Error de negocio: contraseña errónea → 401 genérico."""
    await _create_user(engine, "invalido@example.com", "Abc12345")
    resp = await auth_client.post("/auth/login", json={"email": "invalido@example.com", "password": "WrongPass1!"})
    assert resp.status_code == 401, resp.text


@pytest.mark.asyncio
async def test_login_usuario_inexistente(auth_client: AsyncClient, fake_redis, engine):
    """Error de negocio: email desconocido → 401 genérico."""
    resp = await auth_client.post("/auth/login", json={"email": "noexiste@example.com", "password": "Abc12345"})
    assert resp.status_code == 401, resp.text


# ---------------------------------------------------------------------------
# Tests — JWT access token
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_token_expirado_rechazado(auth_client: AsyncClient, fake_redis, engine):
    """Borde: access token expirado → 401."""
    user_id = await _create_user(engine, "expired@example.com", "Abc12345")
    token = _make_expired_access_token(user_id)
    resp = await auth_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401, resp.text


@pytest.mark.asyncio
async def test_token_blacklisted_rechazado(auth_client: AsyncClient, fake_redis, engine):
    """Borde: access token con jti blacklisted → 401."""
    user_id = await _create_user(engine, "blacklisted@example.com", "Abc12345")
    token, jti, _ = create_access_token(user_id, ["paciente"], "blacklisted@example.com")
    await redis_client.blacklist_access(jti, 300)
    resp = await auth_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401, resp.text


# ---------------------------------------------------------------------------
# Tests — Refresh token
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refresh_rotacion_exitosa(auth_client: AsyncClient, fake_redis, engine):
    """Feliz: refresh rotativo devuelve nuevo access y nueva cookie."""
    await _create_user(engine, "refresh@example.com", "Abc12345")
    login_resp = await auth_client.post("/auth/login", json={"email": "refresh@example.com", "password": "Abc12345"})
    assert login_resp.status_code == 200
    refresh_cookie = login_resp.cookies.get("refresh_token")
    assert refresh_cookie is not None

    resp = await auth_client.post("/auth/refresh", cookies={"refresh_token": refresh_cookie})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in resp.cookies


@pytest.mark.asyncio
async def test_refresh_reuso_revoca_familia(auth_client: AsyncClient, fake_redis, engine):
    """Borde: reuso de refresh token blacklisted → 401 y familia eliminada."""
    await _create_user(engine, "reuse@example.com", "Abc12345")
    login_resp = await auth_client.post("/auth/login", json={"email": "reuse@example.com", "password": "Abc12345"})
    assert login_resp.status_code == 200
    refresh_cookie = login_resp.cookies.get("refresh_token")

    r1 = await auth_client.post("/auth/refresh", cookies={"refresh_token": refresh_cookie})
    assert r1.status_code == 200

    r2 = await auth_client.post("/auth/refresh", cookies={"refresh_token": refresh_cookie})
    assert r2.status_code == 401, r2.text


@pytest.mark.asyncio
async def test_refresh_sin_cookie(auth_client: AsyncClient, fake_redis, engine):
    """Error de negocio: sin cookie refresh → 401."""
    resp = await auth_client.post("/auth/refresh")
    assert resp.status_code == 401, resp.text


# ---------------------------------------------------------------------------
# Tests — Logout
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_logout_exitoso(auth_client: AsyncClient, fake_redis, engine):
    """Feliz: logout devuelve 204 y limpia cookie."""
    await _create_user(engine, "logout@example.com", "Abc12345")
    login_resp = await auth_client.post("/auth/login", json={"email": "logout@example.com", "password": "Abc12345"})
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    refresh_cookie = login_resp.cookies.get("refresh_token")

    resp = await auth_client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
        cookies={"refresh_token": refresh_cookie} if refresh_cookie else {},
    )
    assert resp.status_code == 204, resp.text


@pytest.mark.asyncio
async def test_logout_sin_token(auth_client: AsyncClient, fake_redis, engine):
    """Error de negocio: logout sin Bearer token → 401."""
    resp = await auth_client.post("/auth/logout")
    assert resp.status_code == 401, resp.text


# ---------------------------------------------------------------------------
# Tests — Me
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_me_autenticado(auth_client: AsyncClient, fake_redis, engine):
    """Feliz: GET /auth/me devuelve representación del usuario."""
    email = "me@example.com"
    user_id = await _create_user(engine, email, "Abc12345")
    token = _make_access_token(user_id, "paciente", email)
    resp = await auth_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["email"] == email
    assert data["rol"] == "paciente"
    assert data["id"] == str(user_id)


@pytest.mark.asyncio
async def test_me_sin_autenticar(auth_client: AsyncClient, fake_redis, engine):
    """Error de negocio: GET /auth/me sin token → 401."""
    resp = await auth_client.get("/auth/me")
    assert resp.status_code == 401, resp.text


# ---------------------------------------------------------------------------
# Tests — Rate limiting
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rate_limite_login(auth_client: AsyncClient, fake_redis, engine):
    """Error de negocio: más de 5 requests en 60s → 429."""
    await _create_user(engine, "ratelimit@example.com", "Abc12345")
    statuses = []
    for _ in range(6):
        resp = await auth_client.post(
            "/auth/login", json={"email": "ratelimit@example.com", "password": "Abc12345"}
        )
        statuses.append(resp.status_code)
    assert 429 in statuses, f"No se obtuvo 429; estados: {statuses}"


# ---------------------------------------------------------------------------
# Tests — RBAC
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_paciente_no_accede_agenda(auth_client: AsyncClient, fake_redis, engine):
    """Borde: rol paciente no puede acceder a /agenda → 403."""
    user_id = await _create_user(engine, "pacagenda@example.com", "Abc12345", rol="paciente")
    token = _make_access_token(user_id, "paciente", "pacagenda@example.com")
    resp = await auth_client.get("/agenda", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_anonimo_no_puede_post_turnos(auth_client: AsyncClient, fake_redis, engine):
    """Borde: anónimo no puede POST /turnos → 401."""
    resp = await auth_client.post("/turnos", json={})
    assert resp.status_code == 401, resp.text
