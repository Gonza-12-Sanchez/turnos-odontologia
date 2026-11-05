# Tasks — C-04 Catálogo y configuración

## 1. Gate y persistencia de auditoría

- [x] 1.1 Verificar que C-03 original y su seguimiento correctivo estén archivados y sus pruebas aprobadas antes de iniciar implementación; comprobar paths en archive y spec identity/auth sincronizada. Seguimiento archivado 2026-11-04, sync validado 3/3, Apply aprobado por usuario.
- [x] 1.2 Agregar tests de persistencia de auditoría (actor, acción, snapshots y TIMESTAMPTZ) que fallen por modelo ausente; crear ConfigAudit y registrarlo en metadata, verificando campos y restricciones con los tests. RED ImportError, GREEN persistencia y fecha aware.
- [x] 1.3 Crear migración Alembic 002 para config_audit con FK, checks e índices; probar upgrade/downgrade/upgrade solo en turnos_test y comprobar que las tablas core y EXCLUDE permanecen intactos. Ciclo 001→002→001→002 exit0 en instancia aislada55432, tablas core intactas.
- [x] 1.4 Documentar alcance y reversión de migración en documentación backend; verificar comandos y nombre real de la revisión sin ejecutarlos sobre la BD de desarrollo. Ver docs/configuracion.md.

## 2. Validación y contratos comunes

- [x] 2.1 Agregar tests red→green de schemas create/patch/output y paginación; implementar nombres no vacíos y límites de longitud, UUID, extra=forbid y null solo donde corresponda; verificar errores 422 y conservación de omitidos. RED módulo ausente, GREEN contratos y HTTP.
- [x] 2.2 Agregar tests de enteros estrictos, cero/negativos, float/bool y overflow en tratamientos; implementar duración positiva y precio nullable en centavos dentro de INTEGER, verificando rechazo sin coerción. RED10 casos, GREEN validación de schemas y HTTP.
- [x] 2.3 Agregar tests de fechas aware y rangos de bloqueo, incluyendo PATCH de un solo extremo; implementar validación del estado combinado y verificar rechazo de naive/hasta<=desde. Validación combinada en servicio con schema de alta.
- [x] 2.4 Definir schemas de salida y página items/total/page/page_size con filtro activo y orden estable; verificar OpenAPI y tests de default 1/20, límites 1..100 y activo=false. OpenAPI contrastado para los tres recursos.

## 3. CRUD de sillones con auditoría conjunta

- [x] 3.1 Agregar pruebas HTTP de CRUD sillón para secretaria y 401/403 en todas las operaciones para anónimo/paciente/odontólogo; comprobar fallo por rutas ausentes antes de implementarlas. RED16 fallos por404; GREEN CRUD y matriz RBAC.
- [x] 3.2 Implementar repositorio, servicio y router /api/config/sillones con require_admin, consulta/alta/PATCH/baja lógica y 404; verificar ciclo completo y consultorio activo, inexistente/inactivo.
- [x] 3.3 Persistir evento en la misma UoW por cambio efectivo y registrar actor del contexto; verificar snapshots, rollback forzando fallo de auditoría y rechazo de autor/fecha enviados por cliente. Trigger real de test fuerza falla y verifica rollback de alta/PATCH; limpieza en finally.
- [x] 3.4 Verificar baja con turnos históricos, DELETE repetido sin evento duplicado y reactivación que limpia deleted_at; pasar tests de permanencia de filas/FKs y listado activo/inactivo.
- [x] 3.5 Documentar contrato común y ejemplos ficticios de sillones en documentación API; verificar status, campos y paginación contra OpenAPI y pruebas. docs/configuracion.md.

## 4. CRUD de tratamientos

- [x] 4.1 Agregar pruebas red→green HTTP de CRUD de tratamientos por todos los roles; implementar repositorio/servicio/rutas con auditoría y pasar matriz 201/200/204/401/403/404. RED7 casos por404; GREEN CRUD, permisos y validaciones.
- [x] 4.2 Verificar precio nullable, limpieza explícita a null y números inválidos con 422; comprobar centavos enteros exactos persistidos sin floats.
- [x] 4.3 Agregar prueba de tratamiento usado por un turno y modificar su duración/precio/activo; verificar que inicio/fin y referencias históricas no cambien.
- [x] 4.4 Documentar nombres de campos, unidades centavos y semántica PATCH/activo; verificar ejemplos contra respuestas reales y schemas. docs/configuracion.md.

## 5. CRUD de bloqueos y advertencias

- [x] 5.1 Agregar pruebas red→green de CRUD general/específico con permisos en cada operación; implementar rutas y servicios con auditoría y verificar 401/403 para roles no admitidos y referencia válida a sillón activo. RED10 escenarios por404; GREEN CRUD general/específico y RBAC.
- [x] 5.2 Agregar escenarios de solapamiento general/específico, turnos adyacentes, otros sillones y estados cancelado/ausente/inactivo; implementar consulta agregada y warnings TURNOS_SOLAPADOS con cantidad, verificando persistencia permitida sin modificar turnos.
- [x] 5.3 Verificar PATCH combinado, cambio de alcance a null, reactivación y baja lógica de bloqueos; pasar pruebas de validación y eventos antes/después correspondientes.
- [x] 5.4 Documentar alcance null=todos, zonas horarias, rango semiabierto y advertencias; contrastar ejemplos ficticios con pruebas HTTP y OpenAPI. docs/configuracion.md.

## 6. Verificación integrada de C-04

- [x] 6.1 Ejecutar `python .agents/skills/turnos-core-guardian/scripts/check_turnos_invariants.py backend/app/models backend/alembic/versions` desde raíz y comprobar en PostgreSQL de test EXCLUDE parcial/btree_gist, TIMESTAMPTZ, centavos e índices; emitir veredicto Guardian con evidencia y corregir si bloquea. Guardian OK, evidencia en verification.md.
- [x] 6.2 Ejecutar `python -m pytest` y `python -m ruff check .` desde backend con infraestructura de test disponible; resolver regresiones de core/auth y verificar que la nueva auditoría no rompe limpieza de fixtures. 213 passed; ruff check OK; formato54 archivos OK.
- [x] 6.3 Ejecutar `openspec validate c-04-catalogo-config --strict`, revisar `git status`/`git diff` y presentar archivos, migración y pruebas al usuario; comprobar ausencia de secretos/datos reales y no ejecutar git add/commit/push. Verificación y presentación antes del commit posteriormente autorizado explícitamente por usuario; Archive pendiente de revisión.

## Workflow follow-up

- Solicitar revisión de Apply antes de Archive.
- Guardar progreso por etapa con topic_key `opsx/c-04-catalogo-config/<fase>` mediante Engram si está disponible; no afirmar guardado si falta mem_save.
- Sincronizar delta agenda/catalogo-config, archivar C-04 y marcarlo completo en CHANGES.md después de aprobación y verificación.
- Comprobar spec principal y archivo final; no iniciar C-05 ni posteriores dentro de este pedido.
- Cualquier git add, commit o push requiere confirmación explícita del usuario.
