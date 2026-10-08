# Revisión Docker línea por línea — C-01 (firmada)

> Regla dura "Docker revisado": lectura completa el 2026-10-06 antes de cualquier `build`.
> Archivos: `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile` (+ `.dockerignore` de cada lado).
> Resultado: 1 bug real encontrado y corregido (permisos `npm ci` como non-root). Resto OK con 3 notas.

## docker-compose.yml

| Líneas | Veredicto |
|---|---|
| 3 `postgres:16-alpine` | OK, pinneada como pide el design |
| 4-7 credenciales demo `turnos/turnos` | OK para dev, NO producción: sobrescribir en deploy real |
| 9 `pgdata`, 19 `redisdata` | OK, volúmenes nombrados (datos sobreviven a `down`) |
| 10-14 / 20-24 healthchecks `pg_isready` / `redis-cli ping` | OK |
| 27 `build: ./backend`, 48 `build: ./frontend` | OK, contextos mínimos (hay `.dockerignore` en ambos) |
| 30-31 `env_file: backend/.env` | OK pero el archivo NO existe aún: prerequisite `cp backend/.env.example backend/.env` (ver 3.2) antes del primer `up` |
| 33-34 URLs dev hardcodeadas | OK: pisan al `env_file` por precedencia de Compose y apuntan a los servicios internos; secretos (JWT/MP/WA) sí vienen del env |
| 35-39 / 51-53 `depends_on: service_healthy` | OK, respeta el orden `db → redis → api → frontend` del design |
| 40-45 healthcheck api contra `/api/health` | OK, ejercita el contrato del spec; `start_period: 20s` para el arranque |

## backend/Dockerfile

| Líneas | Veredicto |
|---|---|
| 1 `python:3.12-slim` | OK, coincide con el stack (el 3.13 local es solo tooling) |
| 3-4 `ENV` | OK |
| 8 `adduser appuser` (sintaxis Debian) | OK |
| 10-12 `COPY pyproject + app` + `pip install --no-cache-dir .` | OK; `.dockerignore` deja fuera tests, `.env` y versiones de Alembic |
| 14 `USER appuser` antes de exponer/correr | OK |
| 16-18 `EXPOSE` + `CMD` exec-form uvicorn | OK |
| Sin `HEALTHCHECK` en imagen | Aceptado: el healthcheck vive en Compose (líneas 40-45) |

## frontend/Dockerfile

| Líneas | Veredicto |
|---|---|
| 1 `node:22-alpine AS build` | OK, pinneada |
| 5-6 manifests + `npm ci` (lock verificado presente) | OK, reproducible |
| 8-9 `COPY .` + `npm run build` | OK; `.dockerignore` excluye `node_modules/dist/.env` |
| 15 `adduser -D` (sintaxis Alpine) | OK |
| 17-19 copia `dist` + manifests + `vite.config.ts` | OK (preview necesita la config) |
| 21 `chown -R appuser /app` + 23 `USER` + 25 `npm ci` | CORREGIDO en revisión: sin `chown`, `npm ci` como non-root fallaba con EACCES al escribir `node_modules` |
| 25 `npm ci` completo (sin `--omit=dev`) | OK deliberado: `vite preview` necesita el paquete `vite` |
| 27 `CMD` exec-form preview en 4173 | OK, coincide con `EXPOSE` y el puerto de Compose |

## Firma

Revisado línea por línea. Bloqueante pendiente: sin Docker en esta máquina no se pudo correr `docker compose config` ni el build; la validación ejecutiva queda para 5.1.
