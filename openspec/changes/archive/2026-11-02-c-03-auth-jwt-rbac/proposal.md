# Proposal — C-03 auth-jwt-rbac

## Why

C-02 dejó el modelo de datos núcleo (incluido `Usuario` con `password_hash` y `rol`) pero ningún endpoint de identidad: sin login ni emisión de JWT, ningún change posterior (C-04 config, C-05 disponibilidad, C-06 reserva) puede autenticar usuarios ni aplicar la matriz RBAC (RN-AU-01/02). C-03 introduce la capa de identidad y acceso que desbloquea todo el resto del camino crítico y garantiza que reservar exige paciente con login.

## What Changes

- Endpoints de autenticación: `POST /auth/registro` (alta paciente: crea `Usuario` + `Paciente`, hash bcrypt/argon2, validación teléfono AR), `POST /auth/login` (JWT access + refresh), `POST /auth/refresh` (rotación con blacklist del token anterior en Redis), `POST /auth/logout` (blacklist del access), `GET /auth/me`.
- Claims JWT estándar: `sub`, `roles`, `email`, `jti`, `type`, `iat`, `exp`; refresh entregado en cookie HttpOnly (secure, samesite=lax); expiración del access gobernada por `JWT_EXPIRE_MINUTES`.
- Dependencias FastAPI `require_role()` y `require_admin()` según la matriz RBAC de `03_actores_y_roles.md` (anónimo solo lectura de libres; paciente CRUD propio; odontólogo R agenda; secretaria CRUD total + config), aplicables a toda la API.
- Rate limiting 5/60 s por IP+email en `/auth/login` y `/auth/registro` backed por Redis.
- Decisión de credencial documentada: password simple v1 (IN-10-03 resuelta); OTP-WhatsApp queda como mejora futura y no bloquea este change. Contraseñas hasheadas con bcrypt/argon2; jamás en claro ni en repo.
- Integración con `Usuario`/`Paciente` de C-02 y con `BaseRepository`/`UnitOfWork`; teléfono AR validado a nivel app (RN de C-02 D-08).
- Tests: registro + login feliz; token expirado → 401; refresh rotation invalida el token anterior; rate limit → 429; paciente no accede a `/agenda` (403); anónimo no puede `POST /turnos` (401).

## Capabilities

### New Capabilities

- `identity/auth`: emisión y validación de JWT (access + refresh con rotación y blacklist en Redis), endpoints `/auth/*`, cookie HttpOnly para refresh, y dependencias FastAPI `require_role()`/`require_admin()` que materializan la matriz RBAC para toda la API.

### Modified Capabilities

Ninguna (no cambia el contrato de `core/models` ni `platform/health`; solo se consumen las entidades y el health existentes).

## Impact

- Código nuevo: `backend/app/api/auth.py`, `backend/app/services/auth.py` (o equivalente), `backend/app/shared/security.py` (hashing JWT), dependencias de auth en `backend/app/api/deps.py`, schemas Pydantic de auth.
- Nueva spec: `openspec/specs/identity/auth/spec.md` (al archivar).
- Dependencias: requiere C-02 (archivado). Desbloquea C-04 (`catalogo-config`) y en cadena C-05…C-12.
- Sin breaking changes (no hay endpoints de negocio previos; C-01/C-02 solo dejaron scaffolding y modelos).
- Riesgo principal: blacklist/rotación mal implementada invalidaría la revocación de sesiones; se revisa con `security-and-hardening` y tests de rotación. Secretos (`JWT_SECRET_KEY`) solo por variables de entorno, jamás en repo (regla dura).

## Governance Level

CRITICO (GATE 2 — revisión solo). Cambio fundacional de identidad y acceso; cualquier error en RBAC o revocación se propaga a todos los changes posteriores.

## Open Questions

- IN-10-03 resuelta para v1: password simple (bcrypt/argon2); OTP-WhatsApp queda como mejora (no bloquea). IN-10-02/04 (proveedor WhatsApp / quién paga) siguen perteneciendo a C-08.