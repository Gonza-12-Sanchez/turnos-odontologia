# Proposal — C-01 foundation-setup

## Why

Ningún change del roadmap puede implementarse sin una base ejecutable: hoy el repo solo tiene docs (`knowledge-base/`, `discovery/`, `CHANGES.md`) y cero código. C-01 crea el scaffolding completo + infraestructura base para desbloquear C-02 y todo lo demás.

## What Changes

- Estructura de directorios según `08`: `backend/app/{api,services,workers,cobros,db}`, `backend/tests`, `frontend/src/{features,shared,pages}`, `docker-compose.yml`.
- `backend/`: Python 3.12+, FastAPI 0.115+ con `GET /api/health`, SQLAlchemy 2.x async configurado, Alembic inicializado, `shared/` (settings Pydantic, logger, excepciones de negocio).
- `frontend/`: Vite 6 + React 18 + TypeScript 5, PWA mobile-first, api client JWT base, Tailwind.
- `docker-compose.yml`: `api + db (postgres:16) + redis:7 + frontend`; `.env.example` por sub-proyecto con las 10 variables de `08`.
- GitHub Actions CI: jobs paralelos backend (ruff + pytest smoke) y frontend (tsc + build); secretos solo por `${VAR}`.
- Tests: health check + conectividad DB/Redis en Compose.
- ⚠️ Dockerfiles/Compose generados se revisan línea por línea antes de buildear (flag Snyk en `docker-patterns`, regla dura del proyecto).

## Capabilities

### New Capabilities

- `platform/health`: contrato observable del endpoint de salud/readiness (`GET /api/health` con checks `db` y `redis`) que C-12 y el deploy usan como señal de sistema levantado.

### Modified Capabilities

Ninguna (inventario `openspec list --specs` vacío: proyecto greenfield).

## Impact

- Nuevo código: `backend/`, `frontend/`, `docker-compose.yml`, `.github/workflows/`, `.env.example` (placeholders, jamás secretos).
- Nuevo spec base: `openspec/specs/platform/health/spec.md` (al archivar).
- Desbloquea C-02 (`core-models`) y en cadena todo el roadmap.
- Sin breaking changes (repo sin código previo).
