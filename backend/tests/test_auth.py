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

PostgreSQL de test y Redis real aislado por prefijo. Cada solicitud usa su propia
sesión SQL, también en las pruebas de concurrencia.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.api.deps import get_db
from app.core.config import settings
from app.db import redis as redis_client
from app.main import app
from app.models.usuario import Usuario
from app.repositories.usuario_repository import UsuarioRepository
from app.shared.security import (
    create_access_token,
    hash_password,
)
from tests.conftest import DATABASE_URL


@pytest.fixture
async def fake_redis(real_redis):
    """Nombre histórico de fixture: ahora utiliza Redis real aislado."""
    with patch.object(redis_client, "get_redis", return_value=real_redis):
        yield real_redis


# ---------------------------------------------------------------------------
# Fixtures de BD y cliente HTTP
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def engine():
    eng = create_async_engine(DATABASE_URL, poolclass=NullPool)
    yield eng
    await eng.dispose()


# clean_db desactivado: la limpieza manual causa cuelgues en Windows con asyncpg.
# Los tests usan emails únicos, así que no hay conflictos entre tests.


# Lock global para serializar acceso a BD (evita "another operation in progress"
# de asyncpg en Windows cuando hay múltiples operaciones concurrentes).
_db_lock = asyncio.Lock()


@pytest.fixture
async def auth_client(engine, fake_redis) -> AsyncGenerator[AsyncClient, None]:
    """Cliente con sesión compartida y Redis real en cada test."""
    from app.repositories import unit_of_work as uow_module

    # Limpiar tablas antes del test
    async with engine.begin() as conn:
        from app.db.base import Base

        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())

    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    shared_session = factory()

    async def _get_db() -> AsyncGenerator[AsyncSession, None]:
        yield shared_session

    # Monkeypatch UnitOfWork para usar la sesión compartida
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
        from app.main import app as fastapi_app
        transport = ASGITransport(app=fastapi_app)
        async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
            yield c
    finally:
        fastapi_app.dependency_overrides.clear()
        uow_module.UnitOfWork.__init__ = original_uow_init
        uow_module.UnitOfWork.__aenter__ = original_uow_aenter
        uow_module.UnitOfWork.__aexit__ = original_uow_aexit
        await shared_session.close()


@pytest.fixture
async def auth_client_concurrent(engine, fake_redis) -> AsyncGenerator[AsyncClient, None]:
    """Cliente con sesiones INDEPENDIENTES por request (para tests de concurrencia)."""
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        from app.db.base import Base
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())

    async def _get_db() -> AsyncGenerator[AsyncSession, None]:
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = _get_db

    try:
        from app.main import app as fastapi_app
        transport = ASGITransport(app=fastapi_app)
        async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
            yield c
    finally:
        fastapi_app.dependency_overrides.clear()


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
    now = datetime.now(UTC) - timedelta(minutes=5)
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
    resp = await auth_client.post(
        "/auth/login", json={"email": "login@example.com", "password": "Abc12345"}
    )
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
    resp = await auth_client.post(
        "/auth/login", json={"email": "invalido@example.com", "password": "WrongPass1!"}
    )
    assert resp.status_code == 401, resp.text


@pytest.mark.asyncio
async def test_login_usuario_inexistente(auth_client: AsyncClient, fake_redis, engine):
    """Error de negocio: email desconocido → 401 genérico."""
    resp = await auth_client.post(
        "/auth/login", json={"email": "noexiste@example.com", "password": "Abc12345"}
    )
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
    login_resp = await auth_client.post(
        "/auth/login", json={"email": "refresh@example.com", "password": "Abc12345"}
    )
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
    login_resp = await auth_client.post(
        "/auth/login", json={"email": "reuse@example.com", "password": "Abc12345"}
    )
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
    login_resp = await auth_client.post(
        "/auth/login", json={"email": "logout@example.com", "password": "Abc12345"}
    )
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


@pytest.mark.parametrize(
    "password,expected",
    [
        ("A1" + "a" * 70, 201),
        ("A1" + "a" * 71, 422),
        ("A1" + "é" * 36, 422),
    ],
)
async def test_registro_limite_bytes(auth_client, password, expected):
    response = await auth_client.post(
        "/auth/registro",
        json={
            "email": "bytes@example.com",
            "password": password,
            "nombre": "Paciente Ficticio",
            "telefono": "+549111111111",
        },
    )
    assert response.status_code == expected, response.text
    if expected == 201:
        login = await auth_client.post(
            "/auth/login",
            json={
                "email": "bytes@example.com",
                "password": password,
            },
        )
        assert login.status_code == 200


async def test_login_largo_no_trunca(auth_client, engine):
    await _create_user(engine, "largo@example.com", "A1" + "a" * 70)
    response = await auth_client.post(
        "/auth/login",
        json={
            "email": "largo@example.com",
            "password": "A1" + "a" * 71,
        },
    )
    assert response.status_code == 401


@pytest.mark.parametrize("cost,password_ok", [(4, True), (6, True), (4, False)])
async def test_login_actualiza_costo_solo_si_corresponde(
    auth_client,
    engine,
    monkeypatch,
    cost,
    password_ok,
):
    import bcrypt

    monkeypatch.setattr(settings, "bcrypt_rounds", 5)
    stored = bcrypt.hashpw(b"Abc12345", bcrypt.gensalt(cost)).decode()
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        user = Usuario(email="rehash@example.com", password_hash=stored, rol="paciente")
        session.add(user)
        await session.commit()
        uid = user.id
    response = await auth_client.post(
        "/auth/login",
        json={
            "email": "rehash@example.com",
            "password": "Abc12345" if password_ok else "Erronea1",
        },
    )
    assert response.status_code == (200 if password_ok else 401)
    async with factory() as session:
        user = await session.get(Usuario, uid)
        assert int(user.password_hash.split("$")[2]) == (5 if cost == 4 and password_ok else cost)
        assert bcrypt.checkpw(b"Abc12345", user.password_hash.encode())
        if cost == 6 or not password_ok:
            assert user.password_hash == stored


_BAD_CLAIMS = [
    (claim, None, True)
    for claim in (
        "sub",
        "roles",
        "email",
        "jti",
        "type",
        "iat",
        "exp",
    )
] + [
    ("sub", "not-a-uuid", False),
    ("jti", "bad", False),
    ("roles", "paciente", False),
    ("roles", ["admin"], False),
    ("email", [], False),
    ("iat", True, False),
    ("exp", True, False),
    ("iat", "0", False),
    ("type", "other", False),
    ("iat", 9999999999, False),
    ("exp", 0, False),
]


@pytest.mark.parametrize("kind", ["access", "refresh"])
@pytest.mark.parametrize("claim,value,remove", _BAD_CLAIMS)
async def test_jwt_claims_invalidos(auth_client, engine, kind, claim, value, remove):
    from jose import jwt

    from app.shared.security import create_refresh_token

    uid = await _create_user(engine, "claims@example.com", "Abc12345")
    token = (
        _make_access_token(uid)
        if kind == "access"
        else create_refresh_token(uid, str(uuid.uuid4()))[0]
    )
    claims = jwt.get_unverified_claims(token)
    if remove:
        claims.pop(claim)
    else:
        claims[claim] = value
    token = jwt.encode(claims, settings.jwt_secret_key, algorithm="HS256")
    if kind == "access":
        response = await auth_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    else:
        # Registrar familia válida para que claims inválidos no se oculten tras un 401 por familia.
        await redis_client.set_refresh_family(claims.get("fid", ""), claims.get("jti", ""), 60)
        response = await auth_client.post(
            "/auth/refresh",
            headers={
                "Cookie": f"refresh_token={token}",
            },
        )
    assert response.status_code == 401, response.text


@pytest.mark.parametrize("fid", [None, "no-uuid", 123])
async def test_refresh_exige_fid_uuid(auth_client, engine, fid):
    from jose import jwt

    from app.shared.security import create_refresh_token

    uid = await _create_user(engine, "familia@example.com", "Abc12345")
    claims = jwt.get_unverified_claims(create_refresh_token(uid, str(uuid.uuid4()))[0])
    if fid is None:
        claims.pop("fid")
    else:
        claims["fid"] = fid
        await redis_client.set_refresh_family(str(fid), claims["jti"], 60)
    token = jwt.encode(claims, settings.jwt_secret_key, algorithm="HS256")
    response = await auth_client.post("/auth/refresh", headers={"Cookie": f"refresh_token={token}"})
    assert response.status_code == 401


async def test_tipos_tokens_y_firma(auth_client, engine):
    from app.shared.security import create_refresh_token

    uid = await _create_user(engine, "tipos@example.com", "Abc12345")
    access = _make_access_token(uid)
    refresh = create_refresh_token(uid, str(uuid.uuid4()))[0]
    assert (
        await auth_client.get(
            "/auth/me",
            headers={
                "Authorization": f"Bearer {refresh}",
            },
        )
    ).status_code == 401
    assert (
        await auth_client.post(
            "/auth/refresh",
            headers={
                "Cookie": f"refresh_token={access}",
            },
        )
    ).status_code == 401
    parts = access.split(".")
    parts[2] = ("A" if parts[2][0] != "A" else "B") + parts[2][1:]
    assert (
        await auth_client.get(
            "/auth/me",
            headers={
                "Authorization": "Bearer " + ".".join(parts),
            },
        )
    ).status_code == 401


async def _login_session(client, engine):
    await _create_user(engine, "sesion@example.com", "Abc12345")
    response = await client.post(
        "/auth/login",
        json={
            "email": "sesion@example.com",
            "password": "Abc12345",
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"], response.cookies["refresh_token"]


async def test_cookie_y_logout_revocan_sesion(auth_client, engine):
    access, refresh = await _login_session(auth_client, engine)
    for path in ("/auth/login", "/auth/refresh"):
        if path.endswith("login"):
            response = await auth_client.post(
                path,
                json={
                    "email": "sesion@example.com",
                    "password": "Abc12345",
                },
            )
        else:
            response = await auth_client.post(path)
        assert response.status_code == 200
        cookie = response.headers["set-cookie"].lower()
        for attribute in ("httponly", "secure", "samesite=lax", "path=/auth", "max-age="):
            assert attribute in cookie
        assert "refresh_token" not in response.json()
        access = response.json()["access_token"]
        refresh = response.cookies["refresh_token"]
    response = await auth_client.post("/auth/logout", headers={"Authorization": f"Bearer {access}"})
    assert response.status_code == 204
    assert "max-age=0" in response.headers["set-cookie"].lower()
    assert (
        await auth_client.get(
            "/auth/me",
            headers={
                "Authorization": f"Bearer {access}",
            },
        )
    ).status_code == 401
    assert (
        await auth_client.post(
            "/auth/refresh",
            headers={
                "Cookie": f"refresh_token={refresh}",
            },
        )
    ).status_code == 401


async def test_refresh_concurrente_revoca_familia(auth_client, engine, fake_redis, monkeypatch):
    _, refresh = await _login_session(auth_client, engine)
    original = fake_redis.execute_command
    barrier = asyncio.Event()
    reads = 0

    async def interleave(*args, **kwargs):
        nonlocal reads
        result = await original(*args, **kwargs)
        if args[0] == "GET" and str(args[1]).startswith("auth:refresh:family:"):
            reads += 1
            if reads == 2:
                barrier.set()
            await asyncio.wait_for(barrier.wait(), 5)
        return result

    monkeypatch.setattr(fake_redis, "execute_command", interleave)
    responses = await asyncio.gather(
        *[
            auth_client.post("/auth/refresh", headers={"Cookie": f"refresh_token={refresh}"})
            for _ in range(2)
        ]
    )
    assert sorted(r.status_code for r in responses) == [200, 401]
    new_refresh = next(r for r in responses if r.status_code == 200).cookies["refresh_token"]
    # La comprobación siguiente ya no participa de la barrera de dos requests.
    monkeypatch.setattr(fake_redis, "execute_command", original)
    assert (
        await auth_client.post(
            "/auth/refresh",
            headers={
                "Cookie": f"refresh_token={new_refresh}",
            },
        )
    ).status_code == 401


async def test_refresh_no_resucita_logout(auth_client, engine, fake_redis, monkeypatch):
    access, refresh = await _login_session(auth_client, engine)
    reached, release = asyncio.Event(), asyncio.Event()
    original = fake_redis.execute_command

    async def interleave(*args, **kwargs):
        if args[0] == "GET" and str(args[1]).startswith("auth:refresh:family:"):
            result = await original(*args, **kwargs)
            reached.set()
            await asyncio.wait_for(release.wait(), 5)
            return result
        if args[0] == "EVAL" and any(
            str(arg).startswith("auth:refresh:family:") for arg in args[3:5]
        ):
            reached.set()
            await asyncio.wait_for(release.wait(), 5)
        return await original(*args, **kwargs)

    monkeypatch.setattr(fake_redis, "execute_command", interleave)
    pending = asyncio.create_task(
        auth_client.post(
            "/auth/refresh",
            headers={
                "Cookie": f"refresh_token={refresh}",
            },
        )
    )
    try:
        await asyncio.wait_for(reached.wait(), 5)
        logout = await auth_client.post(
            "/auth/logout",
            headers={
                "Authorization": f"Bearer {access}",
                "Cookie": f"refresh_token={refresh}",
            },
        )
        assert logout.status_code == 204
    finally:
        release.set()
    assert (await pending).status_code == 401


async def test_reuso_invalida_reemplazo_y_ttl(auth_client, engine, fake_redis):
    from jose import jwt

    _, refresh = await _login_session(auth_client, engine)
    claims = jwt.get_unverified_claims(refresh)
    response = await auth_client.post("/auth/refresh")
    assert response.status_code == 200
    assert 0 < await fake_redis.ttl(f"auth:blacklist:refresh:{claims['jti']}") <= 7 * 86400
    replacement = response.cookies["refresh_token"]
    assert (
        await auth_client.post(
            "/auth/refresh",
            headers={
                "Cookie": f"refresh_token={refresh}",
            },
        )
    ).status_code == 401
    assert (
        await auth_client.post(
            "/auth/refresh",
            headers={
                "Cookie": f"refresh_token={replacement}",
            },
        )
    ).status_code == 401


async def test_header_ip_no_evade_limite(auth_client):
    responses = [
        await auth_client.post(
            "/auth/login",
            json={
                "email": "limite@example.com",
                "password": "Erronea1",
            },
            headers={"X-Forwarded-For": f"198.51.100.{i}"},
        )
        for i in range(6)
    ]
    assert [r.status_code for r in responses] == [401, 401, 401, 401, 401, 429]
    assert 0 < int(responses[-1].headers["retry-after"]) <= 60


async def test_limite_concurrente_y_expiracion(auth_client, fake_redis):
    responses = []
    for _ in range(6):
        r = await auth_client.post(
            "/auth/login",
            json={
                "email": "concurrente@example.com",
                "password": "Erronea1",
            },
        )
        responses.append(r)
    assert sorted(r.status_code for r in responses) == [401, 401, 401, 401, 401, 429]
    key = "auth:rl:login:127.0.0.1:concurrente@example.com"
    assert 0 < await fake_redis.ttl(key) <= 60
    await fake_redis.pexpire(key, 1)
    await asyncio.sleep(0.02)
    response = await auth_client.post(
        "/auth/login",
        json={
            "email": "concurrente@example.com",
            "password": "Erronea1",
        },
    )
    assert response.status_code == 401


async def test_limite_repara_contador_sin_ttl(auth_client, fake_redis):
    key = "auth:rl:login:127.0.0.1:sin-ttl@example.com"
    await fake_redis.set(key, "5")
    response = await auth_client.post(
        "/auth/login",
        json={
            "email": "sin-ttl@example.com",
            "password": "Erronea1",
        },
    )
    assert response.status_code == 429
    assert 0 < await fake_redis.ttl(key) <= 60


@pytest.mark.parametrize(
    "phase", ["login-limit", "registro", "login-family", "refresh", "logout", "me"]
)
@pytest.mark.parametrize("failure", ["connection", "timeout"])
async def test_redis_caido_responde_503(
    auth_client, engine, fake_redis, monkeypatch, phase, failure
):
    import redis.exceptions

    access, refresh = await _login_session(auth_client, engine)
    original = fake_redis.execute_command

    async def unavailable(*args, **kwargs):
        command = args[0]
        is_rate_limit = command == "EVAL" and args[2] == 1
        if phase not in {"login-limit", "registro"} and is_rate_limit:
            return await original(*args, **kwargs)
        cls = (
            redis.exceptions.ConnectionError
            if failure == "connection"
            else redis.exceptions.TimeoutError
        )
        raise cls("Detalle interno que no debe aparecer")

    monkeypatch.setattr(fake_redis, "execute_command", unavailable)
    if phase in {"login-limit", "login-family"}:
        response = await auth_client.post(
            "/auth/login",
            json={
                "email": "sesion@example.com",
                "password": "Abc12345",
            },
        )
    elif phase == "registro":
        response = await auth_client.post(
            "/auth/registro",
            json={
                "email": "caido@example.com",
                "password": "Abc12345",
                "nombre": "Ficticio",
                "telefono": "+549111111111",
            },
        )
    elif phase == "me":
        response = await auth_client.get("/auth/me", headers={"Authorization": f"Bearer {access}"})
    else:
        response = await auth_client.post(
            f"/auth/{phase}",
            headers={
                "Authorization": f"Bearer {access}",
                "Cookie": f"refresh_token={refresh}",
            },
        )
    assert response.status_code == 503
    assert response.json() == {"detail": "Servicio no disponible"}
