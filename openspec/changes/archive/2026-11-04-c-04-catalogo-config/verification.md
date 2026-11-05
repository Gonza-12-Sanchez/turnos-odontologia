# Verificación Apply — C-04

Fecha: 2026-11-04. Implementación terminada y revisión de Apply aprobada por el usuario para sincronizar specs y archivar.

## Gate respetado

C-03 original y su seguimiento correctivo están archivados. El usuario aprobó Apply C-03 y su cierre; la spec principal identity/auth quedó sincronizada y validada antes de comenzar C-04. No se implementaron C-05 ni posteriores.

## Implementado

- Quince operaciones de catálogo: POST/GET de colección y GET/PATCH/DELETE por id para sillones, tratamientos y bloqueos.
- Permisos de secretaria activa en todas las operaciones; 401/403 por autenticación/rol vigente en base.
- Paginación, filtros activo/inactivo, orden estable, validación estricta de duración/centavos y rechazo de campos extra/null indebido.
- Bloqueos aware, alcance general o específico y validación de PATCH combinado.
- Advertencias agregadas TURNOS_SOLAPADOS en POST/PATCH; sin cancelar ni modificar turnos, excluyendo adyacencia y estados no bloqueantes.
- Bajas lógicas, reactivación e historial conservado; cambio de duración de tratamiento no recalcula turnos anteriores.
- Auditoría transaccional con autor, fecha y snapshots permitidos. Bloqueo de fila al modificar evita snapshots anteriores desactualizados bajo escrituras concurrentes.

## TDD y pruebas significativas

- RED: modelo de auditoría ausente; GREEN: persistencia con autor/fecha aware y restricciones FK/CHECK.
- RED: schemas de catálogo ausentes; GREEN: números estrictos, null/omitidos, límites y fechas.
- RED: CRUD/RBAC de sillones devolvían404; GREEN: ciclo completo y todos los roles/operaciones.
- RED: siete escenarios de tratamiento sin rutas; GREEN: CRUD, duración inválida e histórico intacto.
- RED: diez escenarios de bloqueo sin rutas; GREEN: CRUD, advertencias y validación de referencias/rango.
- Un trigger real de PostgreSQL fuerza fallo de auditoría: el PATCH y el alta se revierten; quedan catálogo y eventos previos intactos. El trigger se elimina en finally, tras liberar la transacción de lectura.
- OpenAPI contrastado con métodos, schemas, defaults y límites de paginación.

## Resultados finales

Entorno aislado: Python3.14, PostgreSQL18.6 en puerto55432/base turnos_test y Redis8.10.3 loopback6379 con claves prefijadas. No se modificó el PostgreSQL preexistente puerto5432. CI está configurado para PostgreSQL16/Redis7; el job remoto no fue ejecutado en esta sesión.

| Verificación | Resultado |
|---|---|
| `python -m pytest tests/test_config.py -q` | 111 passed |
| `python -m pytest -q --tb=short` (backend completo) | 213 passed; 4 avisos históricos HTTPX |
| `python -m ruff check .` | All checks passed |
| `python -m ruff format --check app tests` | 54 files already formatted |
| `openspec validate c-04-catalogo-config --strict` | válido |
| Migración002 upgrade/downgrade/upgrade | 001→002→001→002 exit0, solo turnos_test |

## Veredicto Guardian: OK

- EXCLUDE: `ex_turno_no_solape` parcial vigente y `btree_gist` presente, comprobados en catálogo PostgreSQL.
- Invariantes: timestamps de agenda y auditoría con zona horaria; precio/monto en INTEGER centavos; FK actor de auditoría ON DELETE RESTRICT y ambos índices presentes.
- Seeds: únicamente datos ficticios; core/models e idempotencia pasan en suite completa.
- Script determinista del Guardian: OK.
- Cierre: revisión de Apply aprobada; spec agenda/catalogo-config sincronizada y validada, Archive autorizado y roadmap marcado `[x]` al cerrar.

## Control de cambios

La implementación quedó registrada en el commit autorizado `898d996`. El usuario aprobó posteriormente el cierre de C-04. Se creó la spec principal `openspec/specs/agenda/catalogo-config/spec.md`, conservando íntegros el propósito y todos los requisitos/escenarios del delta: solo cambian el título y el encabezado de requisitos al formato principal. La validación estricta conjunta pasó 5/5 antes de Archive. El cierre documental y archivo se registran en un commit posterior autorizado; sin push.
