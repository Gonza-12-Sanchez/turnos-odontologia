# Verificación — C-01 foundation-setup (evidencia retroactiva)

> **Aviso de reconstrucción.** Este documento se escribió el **2026-11-04** para dejar en el archivo la evidencia de verificación que faltaba; el cierre original del change fue el **2026-10-06**. Se distingue explícitamente lo **re-verificado en esta sesión** de lo que consta en el **registro original** y no se repitió.

## 1. Registro original del cierre (2026-10-06)

Según `CHANGES.md` §C-01 y `docker-review.md` (revisión Docker firmada el mismo día):

- `docker compose up --build` con escenario feliz del spec (`status: ok`, `db` y `redis` en `up`).
- Escenario degradado en vivo: bajar Redis → `status: degraded`.
- Smoke de conexión DB/Redis dentro de Compose.
- `alembic upgrade head` con migración base vacía → exit 0.
- Revisión Docker línea por línea: 1 bug real corregido (permisos de `npm ci` como non-root) y 3 notas.

Estos puntos **no se re-ejecutaron** en la sesión de reconstrucción (no se levantó el stack completo con `--build`).

## 2. Re-verificado en esta sesión (2026-11-04)

| Verificación | Comando / método | Resultado |
|---|---|---|
| Estructura del monorepo | inspección de árbol | `backend/app/{api,core,db,models,repositories,schemas,services,shared,workers,cobros}`, `frontend/src/{features,shared,pages}`, `docker-compose.yml`, Dockerfiles y `.env.example` por sub-proyecto presentes |
| Spec `platform/health` sincronizada | `openspec validate --specs --strict` | 4/4 specs válidas (incluye `platform/health`) |
| Contrato del health endpoint | `pytest tests/test_health.py` | 4/4 escenarios del spec (feliz, Redis caído, check lento acotado por timeout, acceso anónimo) |
| Health en vivo — feliz | `uvicorn app.main:app` + `GET /api/health` con PostgreSQL y Redis arriba | `200 {"status":"ok","checks":{"db":"up","redis":"up"}}` |
| Health en vivo — degradado | se detiene Redis y se repite `GET /api/health` | `200 {"status":"degraded","checks":{"db":"up","redis":"down"}}` (nunca 500) |
| Manifiesto Compose válido | `docker compose config --quiet` | exit 0 (requiere `cp backend/.env.example backend/.env`, prerequisite ya documentado en `docker-review.md`) |
| Frontend base | `npm run build`, `oxlint`, `vitest run` | build PWA OK (5 entradas precache), lint limpio, 3/3 tests del api client |
| Lint/formato backend | `ruff check .` + `ruff format --check app tests` | All checks passed; 54 files already formatted |
| Sin secretos trackeados | `git ls-files` filtrado por `env` | solo `backend/.env.example` y `frontend/.env.example` |
| Suite backend acumulada | `pytest -q` sobre `turnos_test` + Redis | 213 passed (estado del repo tras C-04, incluye los tests de C-01) |

## 3. Cobertura del spec `platform/health`

| Escenario | Test |
|---|---|
| Sistema completamente levantado (feliz) | `tests/test_health.py::test_happy_todo_levantado` |
| Redis caído degrada sin tumbar el endpoint | `tests/test_health.py::test_error_redis_caido_degrada` |
| Chequeo lento se declara caído pasado el timeout | `tests/test_health.py::test_borde_check_lento_acotado_por_timeout` |
| Acceso anónimo al health check | `tests/test_health.py::test_acceso_anonimo_sin_token` |

## 4. Estado de tareas

`tasks.md`: **10/10** tareas marcadas, sin pendientes.

## 5. Veredicto

**C-01 verificado.** El scaffolding, la configuración base, el contrato de health, el Compose, el CI y el `.env.example` siguen vigentes y coherentes con lo archivado; la spec `platform/health` valida en estricto y sus 4 escenarios pasan tanto en tests como en vivo (ok y degraded). La única diferencia respecto del cierre original es que el levante completo con `docker compose up --build` no se repitió en la reconstrucción.

**Brecha registrada:** el stack completo vía Compose se re-verificará en C-12 (`hardening-e2e`), que exige suite verde en Compose limpio.
