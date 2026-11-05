# Tasks — C-03 auth-jwt-rbac

## 1. Fundamentos: dependencias, config y seguridad

- [x] 1.1 Agregar dependencias `passlib[bcrypt]>=1.7.4` y `python-jose[cryptography]>=3.3.0` a `backend/requirements.txt` (o pyproject) y verificar `pip install` sin errores.
- [x] 1.2 Agregar variables de entorno `JWT_SECRET_KEY`, `JWT_EXPIRE_MINUTES` (default 60), `REFRESH_EXPIRE_DAYS` (default 7), `COOKIE_SECURE` (default true), `COOKIE_SAMESITE` (default lax), `BCRYPT_ROUNDS` (default 12), `FRONTEND_URL` a `backend/app/core/config.py` y `.env.example`, y verificar carga con `python -c "from app.core.config import settings; print(settings.jwt_expire_minutes)"`.
- [x] 1.3 Implementar validacion de `JWT_SECRET_KEY` en startup (fail si placeholder o len < 32 en prod; warning en dev) en el lifespan y verificar que la app no inicia con secreto invalido en prod.
- [x] 1.4 Crear `backend/app/shared/security.py` con `hash_password`/`verify_password` (passlib bcrypt, cost configurable) y helpers `create_access_token`/`create_refresh_token`/`decode_token` (jose, HS256) y verificar import + roundtrip encode/decode en test rapido.
- [x] 1.5 Configurar CORS con origen exacto (`FRONTEND_URL`) y `allow_credentials=True`, mas header `X-Content-Type-Options: nosniff`, y verificar respuesta de preflight con credenciales.
- [x] 1.6 Configurar cliente Redis async con `socket_timeout=2.0` en `backend/app/core/redis.py` (o equivalente) y verificar conexion PING.

## 2. Schemas y repositorios

- [x] 2.1 Crear `backend/app/schemas/auth.py` con `RegistroIn`, `LoginIn`, `TokenOut`, `UserOut`, `RefreshOut` y validadores (password policy min 8 + letra + digito + max 128, email normalizado, telefono AR) y verificar con tests unitarios de validacion (valido/invalido).
- [x] 2.2 Crear `backend/app/repositories/usuario_repository.py` extendiendo `BaseRepository[Usuario]` con `get_by_email` y `get_by_telefono` async y verificar import + query contra DB de test.
- [x] 2.3 Crear `backend/app/repositories/paciente_repository.py` extendiendo `BaseRepository[Paciente]` y verificar import.

## 3. RBAC dependencies

- [x] 3.1 Implementar `get_current_user` en `backend/app/api/deps.py` (extraer Bearer, decodificar access, verificar type=access y no blacklisted, cargar Usuario activo) devolviendo 401 en cualquier fallo, y verificar con token valido/invalido/expirado.
- [x] 3.2 Implementar `require_role(*roles)` y `require_admin()` (alias secretaria) en `deps.py` devolviendo 403 si el rol no esta permitido, y verificar matriz con usuarios de distintos roles.
- [x] 3.3 Implementar `get_optional_user` (devuelve Usuario o None sin bloquear) y verificar que rutas publicas no fallan sin token.

## 4. Rate limiting

- [x] 4.1 Implementar `rate_limit_auth(scope)` en `backend/app/shared/rate_limit.py` (ventana fija 60s, INCR+EXPIRE, clave `auth:rl:{scope}:{ip}:{email_norm}`, limite 5) y verificar contador incrementa y TTL se setea en primer hit.
- [x] 4.2 Integrar rate limit como `Depends` en `/auth/login` y `/auth/registro` ejecutandose antes de la logica de negocio, y verificar respuesta 429 con `Retry-After` al exceder 5 intentos.

## 5. Servicio de auth

- [x] 5.1 Crear `backend/app/services/auth_service.py` con `registrar` (unicidad email/telefono, hash, UoW Usuario+Paciente, 409 en conflicto) y verificar registro exitoso + duplicado 409.
- [x] 5.2 Implementar `login` (busqueda por email, verify password, is_active, emitir access+refresh, setear family key Redis, cookie) con mensaje generico 401 en fallo, y verificar login feliz + credenciales invalidas 401.
- [x] 5.3 Implementar `refresh` con rotacion + deteccion de reuso (D-04) y verificar nuevo access + cookie y blacklist del jti anterior.
- [x] 5.4 Implementar `logout` (blacklist access jti, borrar family, blacklist refresh, limpiar cookie, 204) y verificar idempotencia.
- [x] 5.5 Implementar `me` (devolver UserOut, cargar Paciente si rol paciente) y verificar respuesta para usuario autenticado.

## 6. Endpoints

- [x] 6.1 Crear `backend/app/api/auth.py` con router `/auth` y endpoint `POST /auth/registro` (201) delegando a auth_service, y verificar respuesta 201 + persistencia.
- [x] 6.2 Agregar `POST /auth/login` (200 + cookie) y verificar login feliz + 401 invalido.
- [x] 6.3 Agregar `POST /auth/refresh` (200 + cookie rotada) y verificar rotacion + reuso revoca familia.
- [x] 6.4 Agregar `POST /auth/logout` (204 + cookie cleared) y verificar blacklist del access.
- [x] 6.5 Agregar `GET /auth/me` (200) y verificar respuesta con token valido y 401 sin token.
- [x] 6.6 Registrar el router en la app principal (`backend/app/main.py`) bajo prefijo `/auth` y verificar rutas en `/openapi.json`.

## 7. Hashing bcrypt en threadpool

- [x] 7.1 Ejecutar `hash_password`/`verify_password` via `run_in_threadpool` en los endpoints/servicio para no bloquear el event loop, y verificar que el event loop no se bloquea (test de concurrencia basico).

## 8. Tests de escenarios de spec

- [x] 8.1 Test registro+login feliz: registra usuario, hace login, verifica access token valido y cookie refresh, y `/auth/me` responde 200.
- [x] 8.2 Test token expirado -> 401: genera access con exp pasado y verifica 401 en endpoint protegido.
- [x] 8.3 Test refresh rotation invalida anterior: refresh dos veces con el mismo token inicial; segundo intento responde 401 y familia revocada.
- [x] 8.4 Test rate limit -> 429: 6 requests login mismo IP+email y verifica 429 con Retry-After en el sexto.
- [x] 8.5 Test paciente no accede a `/agenda` (403): login paciente y GET/endpoint agenda responde 403.
- [x] 8.6 Test anonimo no puede POST `/turnos` (401): sin token, POST /turnos responde 401.
- [x] 8.7 Test cookie HttpOnly/Secure/SameSite/Path en login y refresh, y test password almacenado como bcrypt hash.

## 9. Verificacion final

- [x] 9.1 Ejecutar `pytest` y verificar que todos los tests pasan.
- [x] 9.2 Revisar `git status`/`git diff` asegurando solo archivos intencionales y sin secretos ni datos reales.
- [x] 9.3 Ejecutar `openspec validate --change "c-03-auth-jwt-rbac" --strict` y verificar sin errores.

## Workflow follow-up

- Archivar el change tras satisfacer GATE 2 (revision): `/opsx:archive c-03-auth-jwt-rbac`.
- Marcar `[x]` C-03 en `CHANGES.md` al archivar.
- Verificar resultado archivado (spec en `openspec/specs/identity/auth/spec.md`).