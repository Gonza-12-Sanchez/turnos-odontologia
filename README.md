# Turnos Odontología — Gestión de turnos y agenda para consultorios odontológicos

Trabajo de integración (Metodología I): del Discovery al primer Change, con
Spec-Driven Development (OpenSpec) y Active Stack. Mercado objetivo: Argentina.

Estado actual: C-01 `foundation-setup` implementado y verificado 10/10
(`CHANGES.md` marcado `[x]` el 2026-10-06: tests en verde + health checks en vivo ok/degraded).
Herramienta activa: OpenCode (`.opencode/`); scaffolds de otros agentes eliminados.

## Estructura

- `.active-orchestrator-state.json` — estado de la fundación (`step: done`)
- `docs/discovery/checklist-discovery.md` — checklist 11 puntos (canónico)
- `docs/discovery/sources/` — notas por competidor (6)
- `docs/discovery/` — `informe-discovery.md` + `informe-discovery.pdf` (mismo nombre)
- `knowledge-base/` — base de conocimiento (10 canónicos + README)
- `CHANGES.md` — roadmap 12 changes (C-01 `[x]` verificado)
- `openspec/` — specs y changes OpenSpec
- `backend/` — API FastAPI (`app/`, `tests/`, `alembic/`, `Dockerfile`)
- `frontend/` — PWA React+TS+Vite (`src/`, `Dockerfile`)
- `docker-compose.yml` — `api + db (postgres:16) + redis:7 + frontend`
- `.github/workflows/ci.yml` — CI paralelo backend/frontend

## Requisitos

- Python 3.12+, Node 22+, Git, Docker Desktop
- OpenSpec CLI: `npm install -g @fission-ai/openspec`

> Windows/PowerShell: si `openspec` (o `npm`) da error de ExecutionPolicy,
> ejecutarlo vía CMD: `cmd /c "openspec --version"` (vale para `npm`/`npx` también).
> Si `docker` no se reconoce, agregar `C:\Program Files\Docker\Docker\resources\bin` al PATH.

## Instalación

```bash
# Backend (desde la raíz)
pip install -e "./backend[dev]"

# Frontend
cd frontend
npm ci
cd ..

# Variables de entorno (prerequisite antes del primer `up`)
cp backend/.env.example backend/.env
```

## Cómo correr los tests

```bash
# Backend: 4 tests del spec platform/health (feliz, error, borde, público)
python -m pytest backend/tests -v

# Frontend: 3 tests del api client JWT
cd frontend
npm test -- --run
cd ..

# Levantar todo + health check en vivo (requiere Docker + backend/.env)
docker compose up --build -d
curl http://localhost:8000/api/health   # {"status":"ok","checks":{"db":"up","redis":"up"}}
docker compose down -v                   # apaga y limpia al terminar
```

## Tests

Suite C-01 (verificada 2026-10-06, local + Docker real):

| Escenario del spec (`platform/health`) | Test automatizado | Resultado |
|---|---|---|
| Feliz: todo levantado → 200 `ok` | `backend/tests/test_health.py::test_happy_todo_levantado` | ✅ PASS |
| Error: Redis caído → 200 `degraded` | `test_error_redis_caido_degrada` (+ simulacro en vivo `stop redis`) | ✅ PASS |
| Borde: check lento → `down` acotado por timeout | `test_borde_check_lento_acotado_por_timeout` | ✅ PASS |
| Público: sin JWT → 200, nunca 401 | `test_acceso_anonimo_sin_token` | ✅ PASS |
| Api client inyecta Bearer / propaga 401 | `frontend/src/shared/api/client.test.ts` (3 tests) | ✅ PASS 3/3 |
| Health en vivo vía Compose | `GET /api/health` → `ok` / degradado simulado | ✅ PASS |

Detalle de la evidencia en `openspec/changes/archive/2026-10-06-c-01-foundation-setup/` (`tasks.md` 10/10, `docker-review.md`).

## MCP: PostgreSQL (desarrollo)

El agente puede consultar la base de datos de desarrollo mediante el servidor MCP
`@modelcontextprotocol/server-postgres` (solo lectura). Configuración en
`~/.config/opencode/opencode.json` (ver plantilla `docs/skills-mcp/mcp-postgres.opencode.example.json`).

### Requisitos

- Node.js 18+ con `npx`.
- Un Postgres accesible en `localhost:5432` con la base `turnos_test` y el usuario `turnos`/`turnos`
  (puede ser el contenedor `db` del compose o un Postgres local).
- Si el puerto 5432 está ocupado por otro Postgres, detenerlo o cambiar el puerto en la config del MCP.

### Comprobación

```bash
opencode mcp list          # debe mostrar "postgres connected"
```

Ejemplo de invocación real (ejecutado y verificado):

```
postgres_query {"sql":"SELECT current_database() AS db, current_user AS usuario, version() AS version;"}
→ db: turnos_test · usuario: turnos · PostgreSQL 17.10
```

### Solución de problemas

- **`postgres` no aparece en `opencode mcp list`**: revisar que la entrada `mcp.postgres` exista en
  `~/.config/opencode/opencode.json` y que `npx` esté en el PATH.
- **Error de conexión (ECONNREFUSED)**: el Postgres no está levantado o el puerto no coincide.
- **Autenticación fallida**: verificar usuario/contraseña (`turnos`/`turnos`) y que la base `turnos_test` exista.
- El servidor MCP solo acepta `SELECT`/inspección de catálogo; cualquier `INSERT/UPDATE/DELETE/DDL` es rechazado.

## Reglas del dominio

- Nunca almacenar datos reales de pacientes en el repositorio ni en los ejemplos.
- No contactar proveedores ni crear cuentas con datos personales reales.
