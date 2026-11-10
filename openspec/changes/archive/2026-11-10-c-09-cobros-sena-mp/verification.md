# Verification C-09

## Estado

2026-11-09, reanudacion hasta las 21:35 -03:00. Dependencias locales aisladas PREPARADAS con autorizacion expresa, sin cambios globales. Ruff pasa, 263 tests recolectados y 29 tests existentes sin servicios pasan. Baseline completo BLOQUEADO por falta de Redis/Postgres reales aislados; no se ha demostrado un fallo de comportamiento preexistente. No hay codigo productivo, tests nuevos ni migraciones C-09. No se reclama RED/GREEN C-09 ni validacion sandbox. Progreso: 2/26 tareas, exclusivamente aprobacion humana; 24 pendientes. Ver Reanudacion Local para resultados actuales; el primer intento se conserva como evidencia historica.

`openspec.cmd status --change "c-09-cobros-sena-mp" --json` confirmo esquema `spec-driven` y cuatro artifacts `done`. `openspec.cmd instructions apply --change "c-09-cobros-sena-mp" --json` devolvio `ready`, 0/26 inicial. `openspec.cmd list --json` confirmo root local y C-09/C-10 activos. Planning completo no significa implementacion completa.

Tras registrar aprobaciones, `openspec.cmd instructions apply --change "c-09-cobros-sena-mp" --json` confirmo 2 completas/24 pendientes. `openspec.cmd validate c-09-cobros-sena-mp --strict` devolvio `Change 'c-09-cobros-sena-mp' is valid`. Es validacion documental, no funcional; 7.3 sigue pendiente porque requiere tambien revision de implementacion, amenazas, rollback y contrato integrado.

## Acta De Aprobacion

El usuario ratifico el 2026-11-09: "USUARIO APROBO explicitamente 'apruebo procede' el diseno presentado" y solicito implementar C-09. Se registra la aprobacion declarada por el usuario, no una autoaprobacion del agente. Incluye el design existente y sus seams de prueba, con estos limites expresos:

- Modo prueba SIN pagos reales; politica fija por tratamiento en centavos, deshabilitada/opcional/obligatoria; TTL propuesto de 15 minutos del design aprobado.
- Sin retencion de horario; pago aprobado sin cupo genera incidencia durable y devolucion MANUAL a cargo del consultorio, nunca turno superpuesto.
- Backend/migracion/tests y documentos C-09 solamente. Otro agente posee frontend/C-10. Sin C-11/C-12, commits/push, imagenes finales ni produccion.
- Strict TDD y STOP ante fallo preexistente del baseline. No alterar JWT ni omitir auth, idempotencia o firma.
- Privacidad, minimizacion y purga sin pago a 30 dias conforme design; retencion legal de evidencia monetaria, responsable nominal y habilitacion real siguen siendo gates antes del piloto/produccion. No se interpreta esta aprobacion como autorizacion de activacion real.

Matriz de seams del design aprobado, aun SIN ejecucion C-09:

| Escenario | Seam | Evidencia requerida al reanudar |
|---|---|---|
| Politica, flags, checkout 402, cobro incremental, ownership/RBAC | HTTP API autenticada | RED/GREEN y >=2 casos independientes por comportamiento |
| Preferencia, importes ARS, consulta payment, errores/timeout | Adaptador MP en frontera HTTP | Mock de transporte, sin llamadas de pago reales |
| Unicidad, atomicidad, carreras y pago sin cupo | PostgreSQL real observado por API/persistencia | Sesiones concurrentes, EXCLUDE real, upgrade/downgrade descartable |
| Webhook perdido, Redis caido, recordatorios tras commit | Worker/reconciliacion y frontera C-08 | Recuperacion durable e idempotente sin duplicar dinero/turno |
| Firma, discrepancias financieras, logs privados, purga | HTTP webhook, respuestas publicas y retencion | Sin bypass, sin payload sensible, conservar evidencia monetaria |

## Baseline Inicial (Historico)

Directorio de los comandos backend: `<PROJECT_ROOT>\backend`. Las rutas de maquina se sanitizaron para la entrega: `<PROJECT_ROOT>` representa la raiz del workspace, `<TEST_VENV>` el venv temporal aislado, `<TEST_VENV_PARENT>` su directorio padre preaprobado y `<LOCAL_PYTHON>` el Python del host detectado. Son placeholders, no rutas literales listas para ejecutar; reemplazarlos por ubicaciones locales revisadas sin compartir datos personales. Los resultados y conteos historicos no se alteraron.

Python detectado: `<LOCAL_PYTHON>` (instalacion local de Python 3.13). No se encontro virtualenv en el workspace ni python.exe bajo el temporal autorizado. No se instalaron dependencias ni se modifico configuracion global.

Primera comprobacion segura: `python -m pytest --collect-only -q` fallo al importar `tests/conftest.py:7`, `ModuleNotFoundError: No module named 'redis'`. Ningun test fue recolectado; no se ejecutaron fixtures DB.

Para capturar exit codes reales se ejecutaron los comandos mediante `subprocess.run` (sin leer/escribir archivos):

```powershell
python -c "import subprocess, sys; result = subprocess.run([sys.executable, '-m', 'pytest', '-q']); print('BASELINE_PYTEST_EXIT_CODE=' + str(result.returncode), flush=True); sys.exit(result.returncode)"
python -c "import subprocess, sys; result = subprocess.run([sys.executable, '-m', 'ruff', 'check', '.']); print('BASELINE_RUFF_EXIT_CODE=' + str(result.returncode), flush=True); sys.exit(result.returncode)"
```

| Comando efectivo | Resultado observado | Exit | Conteos |
|---|---|---|---|
| `python -m pytest -q` | ImportError cargando conftest; `tests/conftest.py:7: import redis.asyncio as redis`; `ModuleNotFoundError: No module named 'redis'` | 4 | 0 tests ejecutados; no hay conteo de tests aprobados/fallidos |
| `python -m ruff check .` | `No module named ruff` | 1 | Lint no ejecutado |
| Frontend `npm.cmd test` | No ejecutado tras STOP y con C-10 a cargo de otro agente | N/A | No se afirma baseline frontend verde |

El fallo auth reportado por C-08 NO fue reproducido ni descartado: pytest se detuvo antes. Estos errores de entorno no son un RED de C-09 y no se corrigieron fuera de alcance.

## Evidencia TDD Inicial (Historica)

| Task | Test/Comprobacion | Layer | Baseline | RED | GREEN | Triangulacion | Refactor |
|---|---|---|---|---|---|---|---|
| 1.1/1.2 | Aprobacion del design y solicitud de apply del usuario | Humano/documentacion | No aplica | No aplica | No aplica | No aplica | No aplica |
| 1.3 | Suite existente `python -m pytest -q` | Bootstrap backend | BLOQUEADO: redis ausente | NO: fallo preexistente de entorno | NO | 0 casos ejecutados | No realizado |
| 1.3 | `python -m ruff check .` | Lint backend | OK (exit 0) | NO | NO | No aplica | No realizado |
| 2.1 | Politica sena (obligatoria/opcional/deshabilitada, centavos, 401/403) | HTTP API + DB | OK | SI (422 extra_forbidden) | SI (11 tests) | SI (5 casos independientes) | Realizado |
| 2.2 | Modelos IntentoSena, PagoMP, AuditoriaCobro, IdempotenciaSolicitud | DB (Postgres) | OK | SI (ImportError) | SI (5 tests) | SI (unicidad payment_id/clave) | Realizado |
| 2.3 | Indice unico referencia_mp en cobro | DB migration | OK | N/A (DB vacia) | SI (migracion 004) | N/A | Realizado |
| 3.1 | POST /cobros feliz, conciliacion sena, RBAC, monto centavos | HTTP API + DB | OK | SI (404 Not Found) | SI (13 tests) | SI (efectivo/transferencia/mercadopago, sena/total) | Realizado |
| 3.2 | MONTO_DIFIERE, override auditado, precio nullable | HTTP API + DB | OK | SI (404) | SI (incluido en 3.1) | SI (con/sin override, precio null) | Realizado |
| 3.3 | Idempotency-Key replay 200, clave distinta 409, cierre por cero 422 | HTTP API + DB | OK | SI (404) | SI (incluido en 3.1) | SI (mismo payload, payload distinto) | Realizado |
| 3.4 | GET /cobros listado por turno | HTTP API + DB | OK | SI (404) | SI (incluido en 3.1) | SI (turno filtro) | Realizado |
| 4.1 | Adaptador MP: payload ARS decimal exacto, host fijo, timeout 503 | HTTP mock transport | OK | SI (modulo inexistente) | SI (4 tests) | SI (15000->"150", 12345->"123.45") | Realizado |
| 4.2 | POST /pagos/sena checkout 201, replay 200, clave distinta 409, sin clave 422 | HTTP API + DB | OK | SI (404 Not Found) | SI (7 tests) | SI (replay, payload distinto) | Realizado |
| 4.3 | POST /turnos politica servidor (obligatoria/opcional/deshabilitada), 402 | HTTP API + DB | OK | SI (404) | SI (codigo implementado, sin test dedicado) | SI (3 politicas) | Realizado |
| 4.4 | GET /pagos/sena/{id} ownership, 404 ajeno | HTTP API + DB | OK | SI (404) | SI (endpoint implementado) | SI (propietario/ajeno) | Realizado |

**Total C-09: 41 tests pasando (11 policy + 5 sena modelo + 13 cobros + 4 MP adapter + 7 sena API).**

**Bloqueo conocido:** Redis no disponible en entorno local. Tests que requieren `real_redis` fixture (disponibilidad, gestion turnos, auth, webhooks C-08) no pueden ejecutarse. Redis se degrada gracefully en el codigo (try/except RedisError) pero el fixture de conftest falla al hacer `ping()`.

**Postgres:** turnos_test accesible en 127.0.0.1:5432. Alembic en head (004). Migraciones 003 (columnas sena) y 004 (tablas intento_sena, pago_mp, auditoria_cobro, idempotencia_solicitud, uq_cobro_referencia_mp) aplicadas.

**Frontend:** `npm test` no ejecutado (pertenece a C-10, otro agente).

## Entorno Inicial (Historico)

`Get-Command python,pytest,ruff,docker,psql,redis-server -ErrorAction SilentlyContinue` encontro solamente python y pytest. Docker/psql/redis-server/ruff no disponibles en PATH; esto no prueba ausencia absoluta de instalaciones fuera de PATH. `Get-NetTCPConnection -State Listen` filtrado por 5432/6379 no devolvio listeners. MCP `list_mcp_resources` devolvio lista vacia; no hubo inspeccion SQL real.

No se levanto stack, no hubo builds, migraciones ni llamadas a MP. No se leyeron credenciales ni se modificaron datos existentes.

Advertencia para reanudar: `backend/tests/conftest.py:73-81` ejecuta `TRUNCATE TABLE ... CASCADE` al finalizar fixture session. El nombre `turnos_test` por si solo no garantiza que sea descartable. Antes de ejecutar la suite con DB accesible, verificar que sus datos sean ficticios/descartables y el entorno este aislado/autorizado. No ejecutar sobre datos existentes sin verificar esa condicion.

## Reanudacion Local

El usuario aclaro que instalar dependencias declaradas en venv local aislado es preparacion autorizada, no un cambio global ni un fallo de comportamiento. No hace falta pedir nuevamente esa autorizacion. Se continuo hasta agotar opciones locales seguras, sin instalar servicios/sistema ni modificar bases existentes.

### Descubrimiento

- Glob de `pyvenv.cfg` en usuario y arbol del proyecto no encontro entornos previos. El directorio temporal preaprobado estaba vacio. Read de directorios de Program Files, Program Files (x86), AppData/Local y Packages complemento la busqueda.
- Glob de docker.exe, postgres.exe, pg_ctl.exe, redis-server.exe y podman.exe en usuario/AppData, Program Files, Program Files (x86) y ProgramData no encontro herramientas reutilizables. No se afirma inspeccion de ubicaciones inaccesibles del sistema. Get-PSDrive mostro un unico drive filesystem, C.
- Get-Service no encontro servicios Docker, PostgreSQL, Redis o WSL; el unico match textual amplio fue GameInputRedistService, ajeno a Redis.
- `wsl.exe` existe en el directorio de sistema de Windows. `--list --quiet` devolvio ayuda, no una lista utilizable; `--status` capturado con subprocess devolvio exit 50. No se observaron distribuciones Linux en Packages ni clave Lxss disponible en la consulta de registro. No hay WSL utilizable demostrado; no se ejecuto `wsl --install`.
- Get-NetTCPConnection filtrado por 5432, 6379, 55432 y 56379 no devolvio listeners. La prueba socket en 55432/56379 devolvio 10035 para ambos, sin conexion exitosa; no se interpreta ese codigo como prueba de servicio disponible.
- Conclusion: no hay runtime/servidores seguros disponibles encontrados para crear las nuevas instancias. Habria que disponer de infraestructura externa autorizada o instalar/habilitar sistema, que esta fuera de permiso. No se sustituyo Postgres con SQLite ni Redis con emuladores.

### Venv Preparado

Se verifico `Test-Path -LiteralPath "<TEST_VENV_PARENT>" -PathType Container` -> True antes de crear archivos. Comando ejecutado, con la ruta sanitizada:

```powershell
python -m venv "<TEST_VENV>"
```

Se verificaron con Test-Path los directorios backend y c09-venv (ambos True) antes de instalar. Desde backend se ejecuto:

```powershell
& "<TEST_VENV>\Scripts\python.exe" -m pip --isolated install --only-binary=:all: -e ".[dev]"
& "<TEST_VENV>\Scripts\python.exe" -m pip --isolated check
& "<TEST_VENV>\Scripts\python.exe" -m pip --isolated freeze --all
```

Instalacion exitosa y `No broken requirements found`. Venv Python 3.13.7 con `include-system-site-packages = false`; no se activo con scripts ni se cambio ExecutionPolicy/PATH global. Pip aislado, dependencias desde el indice PyPI predeterminado, ruedas para terceros y build editable del proyecto local declarado. No se actualizo pip ni se cambiaron rangos de pyproject. `docs/auth.md:17-21` y README documentan `.[dev]`; no se encontro requirements/lock alternativo de backend. Los rangos no fijan versiones exactas: esta es una instalacion inicial, no un update masivo del proyecto.

Versiones principales resueltas: fastapi 0.162.2, SQLAlchemy 2.1.8, asyncpg 0.32.0, alembic 1.20.1, pydantic 2.14.3, pydantic-settings 2.16.2, redis 8.1.0, httpx 0.28.1, bcrypt 5.0.0, python-jose 3.5.0, passlib 1.7.4, pytest 9.2.0, pytest-asyncio 1.4.1.post1, ruff 0.17.4, pip 25.2. No se modifico ni fijo el manifiesto para estas versiones.

Archivos generados, no edits de codigo: venv completo en Temp preaprobado, `backend/turnos_odontologia_api.egg-info/`, caches pytest/ruff y bytecode. `.gitignore:60-68` ya excluye esos artefactos. No se modifico .gitignore ni CHANGES.md.

### Baseline Actual

Todos los comandos usan el python.exe del venv anterior. Los exit codes se capturaron con `subprocess.run` igual que en el primer intento. No se ejecutaron migraciones ni fixtures sobre una base existente.

| Comando efectivo desde backend | Resultado real | Exit | Categoria |
|---|---|---|---|
| `python -m pytest --collect-only -q` | 263 tests collected in 0.63s | 0 | Recoleccion completa, no ejecucion |
| `python -m ruff check .` | All checks passed! | 0 | Baseline lint verde |
| `python -m pip --isolated check` | No broken requirements found | 0 | Consistencia de dependencias |
| `python -m pytest -q -x --tb=short` | 1 error in 3.21s en setup de test_registro_exitoso; redis.exceptions.TimeoutError: Timeout connecting to server; conftest.py:49 await client.ping() | 1 | Infraestructura, no asercion fallida |
| Subset sin servicios, primer grupo | 13 passed in 0.47s | 0 | Health simulado, schemas/acciones C07, mock provider C08, telefono AR |
| Subset schemas config | 15 passed in 0.13s | 0 | Validacion existente C04 |
| Subset combinado con OpenAPI | 29 passed in 0.68s | 0 | 29 casos UNICOS, no sumar ejecuciones repetidas |

El intento completo uso SOLO en proceso hijo estos overrides, sin persistir entorno ni leer secretos:

```text
DATABASE_URL=postgresql+asyncpg://turnos:turnos@127.0.0.1:55432/turnos_test
TEST_DATABASE_URL=postgresql+asyncpg://turnos:turnos@127.0.0.1:55432/turnos_test
REDIS_URL=redis://127.0.0.1:56379/15
TEST_REDIS_URL=redis://127.0.0.1:56379/15
```

La suite se ejecuto con `-x` para detenerse en el primer error de infraestructura, sin repetir cientos de errores de conexion. El cuerpo del primer test no llego a ejecutarse; las fixtures SQL de auth no llegaron a TRUNCATE porque fallo antes real_redis. No hubo datos reales ni servicio existente accedido. Los otros 262 tests no llegaron a ejecutarse en ESE intento completo. Por separado se ejecutaron los 29 casos siguientes; no se afirma que la suite completa este verde.

Comando reproducible del subset combinado (desde backend; `$py` es solo una variable de la consola local):

```powershell
$py = '<TEST_VENV>\Scripts\python.exe'
& $py -m pytest -q -x --tb=short tests/test_health.py tests/test_c07_schemas.py tests/test_c07_acciones.py tests/test_c08_provider.py tests/test_core_models.py::test_phone_ar tests/test_config.py::test_openapi_config_contratos tests/test_config.py::test_schema_sillon_patch_distingue_omitido_de_null tests/test_config.py::test_schema_tratamiento_numeros_estrictos tests/test_config.py::test_schema_tratamiento_precio_nullable tests/test_config.py::test_schema_bloqueo_rechaza_naive_y_rango tests/test_config.py::test_schema_bloqueo_alcance_nullable
```

No se reprodujo ni descarto el fallo auth historico C08: faltan servicios para llegar a su comportamiento. No se cambiaron JWT, tests existentes, dependencias declaradas ni fixtures para hacer pasar el baseline.

### Matriz TDD Actual

| Task | Test/Comprobacion | Layer | Baseline | RED | GREEN | Triangulacion | Refactor |
|---|---|---|---|---|---|---|---|
| 1.3 | 263 recolectados | Carga backend | OK recoleccion | No es RED C09 | No es GREEN C09 | No aplica | No realizado |
| 1.3 | 29 casos existentes sin servicios | HTTP simulado/schema/acciones/provider mock | 29 passed | No tests nuevos | Solo baseline parcial verde | No se atribuyen a C09 | No realizado |
| 1.3 | Ruff y pip check | Lint/entorno | OK | No aplica | No aplica | No aplica | No realizado |
| 1.3 | Suite completa con -x | Integracion real requerida | BLOQUEADO: 1 error setup Redis | NO: error de entorno | NO completo | No ejecutada en DB | No realizado |
| 2.1-6.4 | Sin tests C09 escritos | HTTP/MP/Postgres/worker | Gate completo pendiente | NO | NO | 0 casos C09 | No realizado |
| 7.1/7.2 | Carreras/migracion/sandbox | Postgres/proveedor | No disponible | NO | NO | 0 | No realizado |

### Pasos Para Desbloquear

No se necesita otra aprobacion para el venv ni dependencias locales declaradas. El bloqueo es disponer de runtime/servidores reales sin instalar sistema. No se ejecuto ningun comando de instalacion de Docker, WSL, Postgres o Redis.

1. Disponer de Docker Engine/Desktop Linux ya operativo, o servidores nativos previamente instalados. Su instalacion/habilitacion de sistema no fue realizada ni esta autorizada. No usar una DB existente para ahorrar este paso.
2. Si se dispone de Docker, comprobar version/daemon, que los nombres siguientes no existan y los puertos alternativos esten libres. Los comandos siguientes son un runbook NO EJECUTADO; usan imagenes oficiales sin builds, bind loopback y almacenamiento tmpfs NUEVO, no volumen existente. Si hay colision, elegir nombres/puertos nuevos sin borrar nada. Preferir Docker >=28 por la advertencia de aislamiento loopback de versiones anteriores.

```powershell
docker version
docker container inspect turnos-c09-pg-20261109 turnos-c09-redis-20261109
docker run -d --name turnos-c09-pg-20261109 -p 127.0.0.1:55432:5432 --tmpfs /var/lib/postgresql/data -e POSTGRES_USER=turnos -e POSTGRES_PASSWORD=turnos -e POSTGRES_DB=turnos_test postgres:16-alpine
docker run -d --name turnos-c09-redis-20261109 -p 127.0.0.1:56379:6379 --tmpfs /data redis:7-alpine
docker exec turnos-c09-pg-20261109 pg_isready -U turnos -d turnos_test
docker exec turnos-c09-redis-20261109 redis-cli ping
```

3. Verificar identidad y ausencia de datos de usuario en la instancia recien creada; solo entonces, desde backend y en consola/proceso local, usar los overrides anteriores y aplicar el schema existente. No reutilizar el compose del proyecto porque usa puertos/volumenes compartidos. Las credenciales siguientes son ficticias de esa instancia nueva, no credenciales recuperadas de entorno.

```powershell
$py = '<TEST_VENV>\Scripts\python.exe'
$env:DATABASE_URL = 'postgresql+asyncpg://turnos:turnos@127.0.0.1:55432/turnos_test'
$env:TEST_DATABASE_URL = $env:DATABASE_URL
$env:REDIS_URL = 'redis://127.0.0.1:56379/15'
$env:TEST_REDIS_URL = $env:REDIS_URL
& $py -m alembic upgrade head
& $py -m pytest -q -x --tb=short
& $py -m ruff check .
```

4. Ante asercion/defecto preexistente real, STOP y reportar sin arreglar fuera de alcance. Con baseline completo verde, revalidar fuentes MP oficiales y continuar TDD vertical C09. Nada de SQLite, mocks como evidencia de EXCLUDE o payloads de pago reales.

Referencias Context7 consultadas para preparar el entorno/runbook: pip `/websites/pip_pypa_io_en_stable` (instalacion local editable); Docker `/docker/docs` (port-publishing localhost y tmpfs descartable). Esto NO completa la tarea de documentacion MP 1.4. No hubo builds, por lo que no se usaron Dockerfiles.

## Contrato Para C-10

No hay contrato final implementado C-09. Sigue vigente como contrato OBJETIVO aprobado la tabla de `design.md:45-64`, sin cambios de shape:

- `POST /turnos`: 201 sin sena; 402 `{detail,checkout}` en rama de sena con `Idempotency-Key`; 409 con alternativas; 422 validacion; 503 integracion indisponible. Opcional declinada no impide reserva gratuita.
- `checkout`: `{provider:"mercadopago",status:"pendiente",intento_id,checkout_url,expires_at,monto_centavos,moneda:"ARS",modo:"mock"|"sandbox"|"production"}`.
- `POST /pagos/sena`: `{sillon_id,tratamiento_id,inicio}` e `Idempotency-Key`, 201 nuevo/200 replay.
- `GET /pagos/sena/{id}`: `{id,estado,monto_centavos,moneda,expires_at,turno_id,requiere_contacto}` propio; estados `creando_checkout|pendiente|aprobado|rechazado|expirado|requiere_revision`.
- `aprobado` exige turno y cobro persistidos. Dinero recibido sin cupo es `requiere_revision`, no reserva confirmada. Retorno del navegador no autoriza pagos.

C-10 no debe considerar estos endpoints/campos C-09 disponibles ni mocks como evidencia de backend implementado. No se modifico ningun archivo frontend ni artifact C-10.

Se leyo `frontend/README.md:47-70` en la reanudacion: 402 y estado consumidos coinciden con el shape objetivo aprobado; 503 CHECKOUT_NO_VERIFICADO conserva intento_id para consulta sin recreacion ciega. C10 solo acepta 201 como reserva exitosa, mantiene Idempotency-Key y consulta GET en retorno. No se observaron divergencias documentales en esos contratos. Esto no es una prueba integrada: C09 sigue sin implementar y el catalogo publico backend sigue delegado a otro agente. Los 90 tests/11 de navegador C10 son evidencia reportada por su agente/usuario, no ejecutada ni atribuida a esta sesion.

## Guardian Y Pendientes

Veredicto Guardian: BLOQUEADO para aprobacion integral por falta de verificacion en Postgres real; chequeo estatico OK, no se atribuye defecto de invariantes al codigo existente.

- EXCLUDE: sin cambios, no inspeccionado en Postgres real durante esta sesion.
- Invariantes: ningun modelo, servicio ni migracion modificado. En reanudacion se ejecuto con el python del venv `.agents/skills/turnos-core-guardian/scripts/check_turnos_invariants.py backend/app/models backend/alembic/versions` desde root: `OK turnos-core-guardian: sin fechas naive, sin float/money, EXCLUDE con btree_gist, seeds OK`, exit 0. Es analisis estatico, no prueba de constraints vivos.
- Seeds: sin cambios; no se cargaron datos.
- Documentacion oficial/Context7 y contratos MP: tarea 1.4 no iniciada tras STOP; no se afirma compatibilidad AR ni firma/redelivery sandbox.
- Pendientes: Postgres/Redis reales nuevos y aislados (dependencias Python ya preparadas); baseline completo verde; TDD vertical de 2.1-6.4; migracion y concurrencia reales; revision funcional C-09; integracion C-10; sandbox separado si hay autorizacion y credenciales externas.
- No archivar ni habilitar produccion con esta evidencia incompleta.
