# Design — C-01 foundation-setup

## Context

Repo hoy: solo docs, cero código (sin `backend/`, `frontend/` ni `docker-compose.yml`). Ver `proposal.md` — Why, y `specs/platform/health/spec.md` para el contrato observable del health check. Restricciones: stack fijo en DD-06 (FastAPI + SQLAlchemy async + Postgres 16 + Redis 7 + Docker; React + TS + Vite), reglas duras en `AGENTS.md` (Docker revisado línea por línea, secrets por env, cero datos reales), CI con jobs paralelos.

## Goals / Non-Goals

**Goals:**
- `docker compose up` levanta api + db + redis + frontend y `GET /api/health` cumple el contrato de `specs/platform/health/spec.md`.
- Base lista para C-02 (modelos + migraciones) sin reestructurar.

**Non-Goals:**
- Ninguna entidad de dominio ni endpoint de negocio (eso es C-02+).
- Auth real, proveedor WhatsApp, Mercado Pago (stubs/env placeholders solamente).

## Decisions

### D-01 — SQLAlchemy 2.x async + asyncpg desde día 1 (no sync transitorio)
Alternativa: arrancar sync y migrar. Se descarta: la regla "async sin bloqueos" y los workers de C-08 exigen async; migrar después cuesta más que configurarlo ahora.

### D-02 — Alembic inicializado con migración vacía, sin tablas
Alternativa: crear tablas en C-01. Se descarta: los modelos llegan en C-02; C-01 deja `alembic.ini` + `env.py` async + migración base vacía.

### D-03 — Settings Pydantic con `.env.example` por sub-proyecto, secretos jamás en repo
Las 10 variables de `08` existen como placeholders; CI usa `${VAR}`. Alternativa: un solo `.env` raíz — se descarta por acoplamiento entre servicios.

### D-04 — Frontend Vite + TS estricto + Tailwind + api client JWT base (sin rutas de negocio)
El client expone `get/post` con inyección de Bearer y manejo 401; las features llegan en C-10/C-11. PWA mínima (manifest + service worker de Vite) mobile-first.

### D-05 — CI en 2 jobs paralelos (backend: ruff + pytest smoke; frontend: tsc + build)
Falla rápido por área; el smoke del spec (escenario feliz) corre contra Compose (DB/Redis reales, sin mocks de infra).

### D-06 — Checks con timeout acotado; el fallo de un check degrada, nunca tumba el endpoint
Implementa el escenario de borde del spec: cada check tiene timeout propio y su lentitud se reporta `down`.

## Risks / Trade-offs

- [Versiones pinneadas (postgres:16, redis:7) pueden quedar viejas] → pinnear igual por reproducibilidad; Renovate/dependabot queda fuera de este change.
- [Tailwind suma tooling al frontend] → se acepta por velocidad en C-10/C-11; si estorba, se quita en C-10.
- [Dockerfiles generados con flag Snyk High Risk] → revisión línea por línea obligatoria antes de buildear (regla dura); nada corre sin esa revisión.
- [Python local 3.13 vs 3.12 del stack] → el container manda (3.12); local solo para tooling.

## Migration Plan

No aplica (sin despliegue previo). Rollback = `git revert` del change. Orden de levante: `db` → `redis` → `api` → `frontend` (healthchecks + `depends_on: service_healthy`).

## Open Questions

Ninguna que cambie el enfoque: proveedor WhatsApp y password-vs-OTP son de changes posteriores (IN-10-02/03/04) y acá solo dejan placeholders de env.
