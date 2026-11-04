# Verificación Apply — C-03 correctivo

Fecha: 2026-11-04. Implementación terminada y revisión de Apply aprobada por el usuario antes de Archive.

## Entorno real

- Python 3.14 en entorno virtual aislado bajo `%LOCALAPPDATA%/Temp/opencode/turnos-venv`.
- Dependencias instaladas con `python -m pip install -e ".[dev]"` desde backend.
- PostgreSQL 18.6 aislado en `127.0.0.1:55432`, base `turnos_test`; migración 001 aplicada con Alembic. El servidor preexistente de puerto 5432 no fue modificado.
- Redis 8.10.3 Windows portable, solo loopback `127.0.0.1:6379`, sin persistencia; SHA256 del archivo contrastado con el digest de la publicación. Suite usa DB15 y prefijo UUID por test, con limpieza exclusiva de sus claves.
- CI configurado para PostgreSQL16/Redis7 efímeros con health checks y migración previa. Configuración YAML inspeccionada; el job remoto no fue ejecutado desde esta sesión.

## Evidencia red → green

| Corte verificable | Estado anterior reproducido | Estado corregido |
|---|---|---|
| Registro 72/73 bytes y multibyte | 2 fallos por ValueError bcrypt, 72 bytes válido | 201 para válido; 422 para exceso, sin truncar |
| Rehash al login | costo 4 seguía en 4 con configuración 5 | costo sube a 5; no se reduce costo 6 ni se cambia con contraseña errónea |
| Claims access/refresh | 23 casos inválidos admitidos | ausentes, tipos inválidos, tiempos incoherentes y UUID inválidos → 401 |
| Dos refresh simultáneos | ambas solicitudes → 200 | 200/401 y familia revocada; reemplazo no utilizable |
| Refresh intercalado con logout | refresh restauraba familia eliminada | refresh → 401; no restaura familia |
| IP falsificada | seis X-Forwarded-For distintos evitaban 429 | mismo cliente sigue limitado; sexto → 429 |
| Contador sin TTL | TTL=-1 permanente | expiración finita restaurada |
| Redis connection/timeout | 8 casos de sesión propagaban errores | 12/12 escenarios de dependencia Redis → 503 genérico |

## Comandos y resultados finales

Desde backend, con `TEST_DATABASE_URL` apuntando a la instancia aislada:

- `python -m pytest -q --tb=short` → **102 passed** (4 avisos de deprecación de HTTPX en tests históricos que usan cookies por request; no errores).
- `python -m ruff check .` → **All checks passed**.
- `python -m ruff format --check app tests` → **48 files already formatted**.

Desde raíz:

- `openspec validate c-03-auth-jwt-rbac-fixes --strict` → válido.
- `git diff --check` → sin errores de whitespace.
- Inspección de `git status` y diffs → solo implementación C-03, tests/CI/documentación asociados y artefactos Propose C-03/C-04 ya existentes. Sin git add, commit ni push.

## Veredicto Guardian: OK

- EXCLUDE: script estático OK y catálogo PostgreSQL de test confirma `ex_turno_no_solape` parcial por `is_active` y estado distinto de cancelado/ausente; extensión `btree_gist` presente.
- Invariantes: `inicio/fin/desde/hasta` son `timestamp with time zone`; precios y montos son INTEGER centavos. Suite de core/models pasa, incluyendo rechazo por solapamiento y seed idempotente.
- Seeds: ficticios; no cambios al seed de dominio. El test ahora utiliza el engine de test configurado, en lugar de una conexión hardcodeada separada.
- Siguiente paso: revisión del usuario, sincronización de delta identity/auth y archivo de C-03 correctivo; después Apply C-04.

## Cierre aprobado

El usuario aprobó el cierre de Apply el 2026-11-04 y autorizó sincronizar/archivar C-03, continuar con C-04 y hacer commit después. Se sincronizó identity/auth preservando título, propósito y requisitos no modificados; `openspec validate --specs` pasó 3/3. C-04 comienza después de este archivo, respetando el roadmap. La autorización de commit no implica push.
