# Tasks — C-01 foundation-setup

## 1. Backend base (FastAPI + SQLAlchemy async + Alembic)

- [x] 1.1 Crear `backend/` (Python 3.12, FastAPI 0.115+, SQLAlchemy 2.x async + asyncpg, Alembic, Pydantic settings, pytest + httpx + ruff) con estructura `app/{api,services,workers,cobros,db}` y verificar `python -m compileall` + `ruff check` limpios
- [x] 1.2 Implementar `GET /api/health` según `specs/platform/health/spec.md` (checks `db`/`redis` con timeout, 200 ok/degraded, público sin auth) + `shared/` (settings, logger, excepciones de negocio) y verificar que los 4 escenarios del spec pasan como pytest smoke
- [x] 1.3 Inicializar Alembic async (`alembic.ini` + `env.py`) con migración base vacía y verificar `alembic upgrade head` corre sin tablas y sin errores

## 2. Frontend base (Vite + React + TS + PWA)

- [x] 2.1 Scaffoldear `frontend/` (Vite 6 + React 18 + TS 5 estricto, Tailwind, manifest PWA) con `src/{features,shared,pages}` y verificar `tsc --noEmit` + `npm run build` en verde
- [x] 2.2 Crear api client JWT base (`shared/api`: get/post con Bearer, manejo 401) y verificar con test unitario que inyecta el header y propaga 401

## 3. Compose + entorno (revisión Docker obligatoria)

- [x] 3.1 Escribir `docker-compose.yml` (`api + db postgres:16 + redis:7 + frontend`, healthchecks, `depends_on: service_healthy`) + Dockerfiles por servicio y verificar revisión línea por línea firmada en el change (regla dura Docker revisado)
- [x] 3.2 Crear `.env.example` por sub-proyecto con las 10 variables de `08` (placeholders, cero secretos) y verificar que ningún `.env` real queda trackeado (`git status` limpio de secretos)

## 4. CI paralelo

- [x] 4.1 Crear workflow GitHub Actions con jobs backend (ruff + pytest smoke del spec) y frontend (tsc + build), secretos solo `${VAR}`, y verificar el YAML con `actionlint` o corrida en rama (push a rama, jamás a main sin pedido)

## 5. Integración y cierre

- [x] 5.1 Levantar `docker compose up --build`, verificar escenario feliz del spec (`status: ok`, ambos `up`) más degradado simulado (bajar redis → `degraded`), y correr el smoke DB/Redis en Compose en verde
- [x] 5.2 Marcar `[x] C-01` en `CHANGES.md` solo cuando 1.1–5.1 estén verificados (no antes)
