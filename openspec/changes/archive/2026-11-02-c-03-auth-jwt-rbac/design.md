# Design — C-03 auth-jwt-rbac

## Context

C-02 dejó el modelo de datos núcleo (`Usuario` con `password_hash` y `rol`, `Paciente`) y la infraestructura async (engine, Redis, settings, `BaseRepository`, `UnitOfWork`), pero ningún endpoint de identidad. C-03 introduce la capa de identidad y acceso que desbloquea C-04…C-12. Ver `proposal.md` — Why/What; las reglas de negocio viven en `knowledge-base/05_reglas_de_negocio.md` (RN-AU-*) y el ERD en `knowledge-base/04_modelo_de_datos.md`. La matriz RBAC está en `knowledge-base/03_actores_y_roles.md`.

Restricciones que moldean el diseño:
- Async puro: SQLAlchemy 2.x async + asyncpg; Redis async; nada sync en el event loop.
- Secretos solo por variables de entorno (`JWT_SECRET_KEY`, `JWT_EXPIRE_MINUTES`); jamás en repo (regla dura).
- `TIMESTAMPTZ` y centavos no aplican a auth (no nuevas tablas); se reusan `Usuario`/`Paciente` de C-02.
- RN-AU-01: reservar exige paciente con login; ver horarios libres es público.
- RN-AU-02: 3 roles (`paciente`, `odontologo`, `secretaria`); matriz explícita.
- IN-10-03 resuelta para v1: password simple (bcrypt); OTP-WhatsApp queda como mejora futura y no bloquea.
- Rate limiting 5/60 s por IP+email en `/auth/login` y `/auth/registro`, backed por Redis.
- Sin datos reales en seeds/fixtures (RN-GL-02).

## Goals / Non-Goals

**Goals:**
- Endpoints `/auth/registro`, `/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/me` con contratos claros y respuestas tipadas.
- Emisión y validación de JWT access + refresh con rotación y blacklist en Redis.
- Refresh entregado en cookie HttpOnly (secure, samesite=lax); access governed by `JWT_EXPIRE_MINUTES`.
- Dependencias FastAPI `get_current_user`, `require_role(*roles)`, `require_admin()` que materializan la matriz RBAC para toda la API.
- Rate limiting 5/60 s por IP+email en login/registro backed por Redis.
- Registro de paciente: crea `Usuario` (rol `paciente`) + `Paciente` en una sola transacción (UoW), con hash bcrypt y teléfono AR validado.
- Tests de rotación, expiración, rate limit y RBAC (401/403).

**Non-Goals:**
- No nuevas tablas ni migración Alembic (reusa `Usuario`/`Paciente` de C-02).
- No OTP-WhatsApp ni proveedor WhatsApp (IN-10-02/04, C-08) — password simple v1.
- No Mercado Pago ni cobros (C-09).
- No frontend ni pantallas de login/registro (C-10/C-11).
- No multi-rol por usuario (v1 un rol por `Usuario`); claim `roles` es lista para evolución futura.
- No refresh token en DB (stateless JWT + Redis blacklist/family).
- No SSO/OAuth externo.

## Decisions

### D-01 — Hashing de contraseñas: bcrypt (cost 12) vía `passlib`

Contraseñas hasheadas con `passlib.context.CryptContext(schemes=["bcrypt"], deprecated="auto")`, cost factor 12 (configurable por env `BCRYPT_ROUNDS`, default 12). Nunca se almacenan en claro ni se loguean.

- Alternativa considerada: argon2id (más moderno, memory-hard, recomendado por OWASP). Se descarta para v1 por simplicidad de dependencia y compatibilidad con el ecosistema FastAPI/passlib; el `CryptContext` permite agregar `argon2` como scheme secundario y migrar hashes de bcrypt a argon2 en el próximo login sin romper usuarios existentes (re-hash transparente). Si se requiere mayor dureza, cambiar `schemes=["argon2"]` en una sola línea.

Dependencia nueva: `passlib[bcrypt]>=1.7.4`.

### D-02 — Librería JWT: `python-jose[cryptography]`

Firma/verificación con `jose.jwt` (HS256), usando `JWT_SECRET_KEY` como secreto simétrico. Elegida por alineación con la documentación oficial de FastAPI y el patrón `OAuth2PasswordBearer`.

- Alternativa considerada: PyJWT (más liviano y mantenido). Se descarta por consistencia con los tutoriales FastAPI y para reusar `OAuth2PasswordBearer`/`HTTPBearer` sin adaptadores; la superficie usada (`encode`/`decode`) es compatible si se migra.

Dependencia nueva: `python-jose[cryptography]>=3.3.0`.

### D-03 — Claims del JWT

Access y refresh comparten el mismo conjunto base; se distinguen por `type`:

| Claim | Tipo | Descripción |
|---|---|---|
| `sub` | string (UUID) | id del `Usuario` |
| `roles` | array[string] | roles del usuario (v1: `["paciente"]` etc.) |
| `email` | string \| null | email del usuario (si existe) |
| `jti` | string (UUID) | id único del token (para blacklist/rotación) |
| `type` | string | `"access"` o `"refresh"` |
| `fid` | string (UUID) | family id del refresh (solo refresh; identifica la sesión de refresh) |
| `iat` | int (unix) | issued at |
| `exp` | int (unix) | expiration |

Access token: `type="access"`, TTL = `JWT_EXPIRE_MINUTES` (default 60). No lleva `fid`.
Refresh token: `type="refresh"`, TTL = `REFRESH_EXPIRE_DAYS` (default 7 días), lleva `fid`.

Algoritmo: `HS256`. Issuer/audience no se incluyen en v1 (YAGNI); se puede agregar `iss`/`aud` sin romper porque la validación solo exige los claims listados.

### D-04 — Rotación de refresh + blacklist en Redis

Estrategia de revocación stateless con Redis como store de revocación/familia:

- **Blacklist de access**: clave `auth:blacklist:access:{jti}` con valor `"1"` y TTL = segundos restantes hasta `exp` (máx. 60 min). Consultada en `get_current_user` para rechazar tokens revocados antes de expirar.
- **Familia de refresh**: clave `auth:refresh:family:{fid}` con valor = jti del refresh vigente y TTL = TTL del refresh (7 días). Permite detección de reuso.
- **Blacklist de refresh rotado**: clave `auth:blacklist:refresh:{jti}` con valor `"1"` y TTL = segundos restantes hasta `exp`. Se setea al rotar.

Flujo de `/auth/refresh`:
1. Decodificar y validar el refresh (firma, `exp`, `type="refresh"`).
2. Si `jti` está en `auth:blacklist:refresh:{jti}` → **reuso detectado** → borrar `auth:refresh:family:{fid}` (revoca la familia) y responder 401. El usuario debe re-loguearse.
3. Si la familia no existe o el jti almacenado ≠ jti presentado → 401 (token inválido/expirado/rotado fuera de banda).
4. Si coincide → rotar: setear blacklist sobre el jti viejo (TTL restante), generar nuevo `jti` (y mantener el mismo `fid`), actualizar `auth:refresh:family:{fid}` al nuevo jti, emitir nuevo access + nuevo refresh.
5. Setear la nueva cookie HttpOnly con el refresh rotado.

Flujo de `/auth/logout`: blacklist del access jti (TTL restante), borrar `auth:refresh:family:{fid}` del refresh actual (si se puede decodificar del cookie), limpiar cookie. Idempotente.

Flujo de `/auth/login`: emitir access + refresh con nuevo `fid` (UUID4) y setear family key.

Trade-off: la detección de reuso revoca la familia completa ante un segundo uso concurrente del mismo refresh (race). Esto es intencionalmente conservador (seguridad > UX); el cliente debe serializar refreshes o re-loguearse.

### D-05 — Cookie HttpOnly para refresh

- Nombre: `refresh_token`.
- Atributos: `HttpOnly=True`, `Secure=settings.cookie_secure` (default `True`; en dev local se puede setear `COOKIE_SECURE=false`), `SameSite="lax"`, `Path="/auth"`, `Max-Age=REFRESH_EXPIRE_DAYS*86400`.
- El frontend nunca lee el refresh (HttpOnly); el access se devuelve en el body JSON y se guarda en memoria (no localStorage) para mitigar XSS.
- CORS: `allow_credentials=True`, `allow_origins=[settings.frontend_url]` (origen exacto, no `*` cuando hay credentials).

Variables de entorno nuevas:
- `REFRESH_EXPIRE_DAYS: int = 7`
- `COOKIE_SECURE: bool = True`
- `COOKIE_SAMESITE: str = "lax"` (validar in {lax, strict, none})
- `BCRYPT_ROUNDS: int = 12`

### D-06 — Rate limiting 5/60 s por IP+email (Redis)

- Algoritmo: ventana fija de 60 s con contador `INCR` + `EXPIRE` (primer hit setea TTL). Límite 5 por ventana.
- Clave: `auth:rl:{scope}:{ip}:{email_norm}` donde `scope ∈ {login, registro}`, `email_norm = email.strip().lower()` (o `"_"` si no aplica, e.g. registro sin email previo — se usa el email del body).
- IP: `request.client.host`; si hay `X-Forwarded-For`, tomar el primer elemento (documentar que el proxy debe sanitizar el header; en prod detrás de reverse proxy confiable).
- Respuesta al exceder: `429 Too Many Requests` con header `Retry-After: <segundos restantes del TTL>` y body `{"detail": "Demasiados intentos. Reintentá en N segundos."}`.
- Aplicar como dependencia `Depends(rate_limit_auth(scope))` en `/auth/login` y `/auth/registro`, ejecutado antes de la lógica de negocio (fail-fast).
- Trade-off: ventana fija permite ráfagas al límite de ventana; aceptable para v1. Sliding window con ZSET queda como mejora.

### D-07 — RBAC: matriz y dependencias FastAPI

Roles: `paciente`, `odontologo`, `secretaria`. Matriz (de `03_actores_y_roles.md`):

| Rol → Recurso | Horarios libres | Turno propio | Turno ajeno | Agenda del día | Cobros | Config |
|---|---|---|---|---|---|---|
| Anónimo | R | — | — | — | — | — |
| Paciente | R | CRUD propio | — | — | R propios | — |
| Odontólogo | R | R (sus pacientes) | — | R | R | — |
| Secretaria | R | CRUD | CRUD | CRUD | CRUD | CRUD |

Dependencias (en `backend/app/api/deps.py`):
- `get_current_user(request, db) -> Usuario`: extrae Bearer del header `Authorization`, decodifica access token, verifica `type="access"` y no blacklisted, carga `Usuario` por `sub`, verifica `is_active`. 401 si falta/inválido/expirado/revocado.
- `require_role(*allowed: str) -> Callable`: factory que envuelve `get_current_user` y exige `user.rol in allowed`, si no 403. Uso: `Depends(require_role("paciente"))`, `Depends(require_role("odontologo", "secretaria"))`.
- `require_admin()`: alias de `require_role("secretaria")` (secretaria es el rol administrativo total). Endpoints de config/cobros usan `require_admin()` o `require_role("secretaria")`.
- `get_optional_user`: variante que devuelve `Usuario | None` para rutas públicas que enriquecen respuesta si hay login (e.g. horarios libres). No bloquea.

Ownership (CRUD propio): los servicios de negocio verifican que el recurso pertenezca al `current_user` cuando el rol es `paciente` (e.g. turno.paciente.usuario_id == user.id); si no, 403/404. Odontólogo/secretaria según matriz.

Endpoints públicos (sin dependency): `/api/health`, `/api/horarios` (libres), `/auth/registro`, `/auth/login`, `/auth/refresh`, webhooks (firmados, C-08/C-09).

### D-08 — Servicio de auth (capas)

Estructura (fastapi-templates):
```
backend/app/
  api/
    auth.py            # router /auth/* (endpoints delgados)
    deps.py            # get_current_user, require_role, require_admin, get_optional_user
  services/
    auth_service.py    # lógica de negocio (registro, login, refresh, logout, me)
  repositories/
    usuario_repository.py   # BaseRepository[Usuario] + lookups por email/telefono
    paciente_repository.py  # BaseRepository[Paciente]
  schemas/
    auth.py            # Pydantic: RegistroIn, LoginIn, TokenOut, UserOut, RefreshOut
  shared/
    security.py        # hashing (passlib) + JWT encode/decode helpers
```

- `auth_service.registrar(db/uow, payload)`: validar teléfono AR (reusa `validate_ar_phone`), verificar unicidad email/teléfono (409 si duplicado), hashear password, crear `Usuario(rol="paciente")` + `Paciente` en la misma UoW, commit, devolver `UserOut`. No emite tokens (login separado).
- `auth_service.login(uow, email, password, ip)`: rate limit ya aplicado en endpoint; buscar usuario por email; verificar hash (`verify_password`); si inactivo o credenciales inválidas → 401 genérico (no revelar cuál falló); emitir access+refresh, setear family key, devolver `TokenOut` (access en body) + cookie refresh.
- `auth_service.refresh(uow, refresh_cookie, ip)`: implementar D-04; devolver nuevo access en body + nueva cookie.
- `auth_service.logout(uow, access_token, refresh_cookie)`: blacklist access, borrar family, limpiar cookie.
- `auth_service.me(user)`: devolver `UserOut` desde el `Usuario` ya cargado.

Repositorios concretos instancian `BaseRepository(session, Model)` y agregan `get_by_email`, `get_by_telefono` (query async con `select`).

### D-09 — Validación y unicidad de credenciales

- Email: `EmailStr` de Pydantic; normalizado a lower-case en servicio.
- Teléfono: reusa `validate_ar_phone` (D-08 de C-02) en el schema de registro.
- Password: mínimo 8 caracteres, al menos una letra y un dígito (validador Pydantic); tope 128 (evitar DoS por hash de contraseñas largas). No se almacena nunca en claro.
- Unicidad: `Usuario.email` ya tiene índice único (C-02); `Usuario.telefono` no es único en el modelo actual — agregar índice único en `telefono`? El modelo C-02 no lo declaró. Para v1, la unicidad de teléfono se enforce en servicio (check previo) + índice único opcional. Decisión: agregar índice único `uq_usuario_telefono` en una mini-migración? El plan de migración dice "none". Para no romper, el servicio hace check + captura `IntegrityError` y devuelve 409. Si se quiere índice, sería una migración `002` (fuera de scope de C-03; diferido a C-04 si hace falta). Documentado como trade-off.

### D-10 — Seguridad operativa

- `JWT_SECRET_KEY` obligatorio y distinto de `"CHANGE-ME"`: validar en startup (`lifespan`) y fallar rápido si es el placeholder (o si `len < 32`). En dev se permite con warning.
- CORS con origen exacto (`FRONTEND_URL`) y `allow_credentials=True`.
- Headers de seguridad básicos (CSP queda en frontend/C-10; backend añade `X-Content-Type-Options: nosniff`).
- Logs: nunca loguear passwords, tokens ni PII sensible; loguear solo `user_id`, `ip`, `scope` en rate limit.
- Timeouts: decodificación JWT sin I/O; operaciones Redis con timeout implícito del cliente (configurar `socket_timeout=2.0`).
- Blacklist con TTL acotado evita crecimiento infinito de Redis.

### D-11 — Estructura de respuestas (schemas)

```
RegistroIn:  { email: EmailStr, password: str, nombre: str, telefono: str, obra_social?: str }
LoginIn:     { email: EmailStr, password: str }
TokenOut:    { access_token: str, token_type: "bearer", expires_in: int (segundos) }
UserOut:     { id: UUID, email: str|null, rol: str, nombre?: str (paciente), telefono?: str }
RefreshOut:  (sin body; solo cookie + 204)  -- o { ok: true }
```
`/auth/refresh` devuelve 204 No Content con nueva cookie y el nuevo access en header? Decisión: devolver 200 con `TokenOut` (access en body) + cookie refresh rotada, para que el cliente actualice el access en memoria. `/auth/logout` devuelve 204.

## Entity Definitions

No nuevas tablas. Se reusan:
- `Usuario` (C-02): `id`, `email` (único), `telefono`, `password_hash`, `rol`, `is_active`, audit. Se usa `password_hash` real (bcrypt) en lugar del placeholder.
- `Paciente` (C-02): `id`, `usuario_id` (único FK), `nombre`, `telefono`, `obra_social`, `notas`, audit.

Persistencia en Redis (no DB):
- `auth:blacklist:access:{jti}` (string, TTL restante)
- `auth:blacklist:refresh:{jti}` (string, TTL restante)
- `auth:refresh:family:{fid}` (string jti, TTL refresh)
- `auth:rl:{scope}:{ip}:{email}` (counter int, TTL 60s)

No cambios al esquema SQL ni migración. El índice único de `usuario.email` ya existe (C-02, `uq_usuario_email`).

## Auth Service — flujos detallados

**Registro (`POST /auth/registro`):**
1. Validar body (Pydantic: email, password policy, teléfono AR, nombre).
2. Rate limit check (scope=registro, ip+email).
3. Abrir UoW; verificar unicidad email y teléfono (409 si existe).
4. Hashear password.
5. Crear `Usuario(email, telefono?, password_hash, rol="paciente")` + `Paciente(usuario_id, nombre, telefono, obra_social)`.
6. Commit. Devolver `UserOut` (201).

**Login (`POST /auth/login`):**
1. Rate limit check (scope=login, ip+email).
2. Buscar `Usuario` por email; si no existe o password no verifica o `is_active=False` → 401 (mensaje genérico, mismo para todos los casos, para no filtrar existencia).
3. Generar `fid` (UUID4), access jti, refresh jti.
4. Setear `auth:refresh:family:{fid}` = refresh jti (TTL refresh).
5. Setear cookie refresh (D-05).
6. Devolver `TokenOut` (access, token_type, expires_in) (200).

**Refresh (`POST /auth/refresh`):**
1. Leer cookie `refresh_token`; si falta → 401.
2. Decodificar; si inválido/expirado → 401.
3. Ejecutar lógica D-04 (reuso/familia/rotación).
4. Setear nueva cookie; devolver `TokenOut` con nuevo access (200) o 204 si solo cookie. (Elegido 200+body por D-11.)

**Logout (`POST /auth/logout`):**
1. Requiere access válido (`get_current_user`); si no, 401.
2. Blacklist access jti (TTL restante).
3. Si hay cookie refresh, decodificar (sin verificar exp estrictamente) y borrar family key; setear blacklist refresh.
4. Limpiar cookie (Max-Age=0).
5. Devolver 204.

**Me (`GET /auth/me`):**
1. `get_current_user` dependency.
2. Cargar Paciente si rol=paciente (para `nombre`/`telefono`).
3. Devolver `UserOut`.

## Security

- Secretos solo por env (`JWT_SECRET_KEY`, `JWT_EXPIRE_MINUTES`, `REFRESH_EXPIRE_DAYS`, `COOKIE_SECURE`, `BCRYPT_ROUNDS`); `.env.example` actualizado con placeholders; `.env` real no commiteado.
- `JWT_SECRET_KEY` validado en startup: si es `"CHANGE-ME"` o longitud < 32 → error fatal en producción; warning en dev.
- Passwords: bcrypt cost 12; nunca en claro, nunca en logs, nunca en repo (seeds usan hash placeholder bcrypt de una contraseña ficticia, no la contraseña).
- Tokens: HS256; `jti` único (UUID4) para revocación; blacklist con TTL acotado.
- Rate limiting en login/registro (D-06) contra brute force.
- CORS con origen exacto + credentials.
- No `any` en TS (frontend, C-10/C-11) — no aplica aquí pero el cliente debe tipar `TokenOut`.
- Async puro: hashing bcrypt es CPU-bound y bloqueante → ejecutar en threadpool (`run_in_threadpool` de FastAPI/Starlette) para no bloquear el event loop. Decodificación JWT y Redis son async/light.
- Redis timeouts (`socket_timeout=2.0`) y manejo de errores: si Redis no disponible, login falla con 503 (fail-closed para seguridad) en lugar de permitir sin rate limit/blacklist.

## Migration Plan

No hay migración: no se crean ni modifican tablas. Prerrequisito: migración `001` de C-02 aplicada (tablas `usuario`, `paciente`, índices). Pasos de despliegue:
1. Agregar dependencias (`passlib[bcrypt]`, `python-jose[cryptography]`) al entorno/imagen.
2. Actualizar `.env`/secrets con `JWT_SECRET_KEY` (≥32 chars aleatorios), `JWT_EXPIRE_MINUTES`, `REFRESH_EXPIRE_DAYS`, `COOKIE_SECURE`.
3. Aplicar configuración CORS (`FRONTEND_URL`).
4. Reiniciar API. No `alembic upgrade` adicional.

Rollback: revertir el código del change; no hay cambios de schema que revertir. Los tokens emitidos quedan inválidos si cambia `JWT_SECRET_KEY` (rotación de secreto = logout global), lo cual es un mecanismo de revocación de emergencia.

## Risks / Trade-offs

- [Robo de access token (XSS)] → access de vida corta (60 min) y guardado en memoria (no localStorage); refresh en HttpOnly cookie; CORS estricto. Mitigación adicional futura: binding a fingerprint (no en v1).
- [Robo de refresh cookie (CSRF/XSS)] → HttpOnly + SameSite=lax + Secure + Path=/auth; rotación con detección de reuso revoca la familia.
- [Race condition en refresh concurrente] → detección de reuso revoca la familia (conservador); el cliente debe serializar. Mitigación: un solo refresh in-flight por cliente (mutex en frontend, C-11).
- [Rate limit bypass por IP (botnets/proxies)] → límite por IP+email; para registro, email del body. Mitigación adicional: CAPTCHA en frontend (futuro) y límite global por email.
- [Hashing bcrypt bloquea event loop] → ejecutar en threadpool; cost factor 12 (~250 ms) aceptable.
- [Redis caído] → fail-closed (503) para login/refresh/logout; health check reporta redis. Mitigación: Redis con restart policy en Compose.
- [Secret débil/placeholder en prod] → validación en startup falla rápido.
- [Unicidad de teléfono solo a nivel servicio] → posible race; mitigación: captura de `IntegrityError` → 409; índice único diferido.
- [No revocación instantánea de access sin blacklist] → blacklist consultada en cada request con TTL; costo O(1) Redis. Aceptable.
- [Clock skew] → usar `datetime.now(timezone.utc)` y tolerancia implícita de jose (leeway 0); servidores deben tener NTP. Documentado.

## Open Questions

- OTP-WhatsApp para pacientes (IN-10-03) queda como mejora futura; v1 usa password. Si se decide OTP, se agrega un flujo `/auth/otp/*` sin romper el actual (D-08 extensible).
- Proveedor WhatsApp y quién paga (IN-10-02/04) pertenecen a C-08; no bloquean C-03.
- Si registro debe emitir tokens automáticamente (auto-login) — decisión actual: no (login separado). Revisable en C-10 sin cambiar specs si se agrega flag.
- Índice único en `usuario.telefono` — diferido; evaluar en C-04 si el catálogo lo requiere.
- Multi-rol por usuario (claim `roles` ya es lista) — sin cambios de schema; se habilita cuando un change lo necesite.
- Si `COOKIE_SAMESITE=none` se requiere en prod cross-site, exige `Secure=True` y HTTPS; documentado como configuración.
