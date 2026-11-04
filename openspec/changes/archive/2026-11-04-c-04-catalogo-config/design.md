# Design — C-04 Catálogo y configuración

## Context

Ver `proposal.md` para motivación. `Sillon`, `Tratamiento` y `Bloqueo` existen con AuditMixin y checks SQL. Falta router de configuración y el mixin no identifica autor. `require_admin()` ya restringe a secretaria. El sistema es de una sede; no hay contrato previo de paginación de catálogo.

## Goals / Non-Goals

**Goals:** separar API → servicio → repositorio, usar validación estricta y una transacción para cada cambio y su auditoría, mantener invariantes e historial.

**Non-Goals:** cálculo de libres o reserva (C-05), gestión de turnos/sobreturnos (C-06), UI o endpoints administrativos adicionales.

## Decisions

### D-01 — Contrato uniforme y permisos antes de operar

Router `/api/config` con `Depends(require_admin())` y usuario resuelto disponible para auditoría. Cada recurso ofrece POST colección (201), GET colección (200), GET `/{id}` (200), PATCH `/{id}` (200) y DELETE `/{id}` (204). Usar PATCH para actualización parcial en vez de duplicar PUT. No autenticado 401, paciente/odontólogo 403, id inexistente 404, entrada inválida 422. RBAC se verifica también en lectura. Payloads no aceptan atributos de auditoría ni autor del cliente.

Listado `{items, total, page, page_size}`; `page>=1`, `1<=page_size<=100`, defaults 1/20. Filtro opcional `activo: bool`, por defecto true; omitir filtro explícitamente con el valor ausente no significa listar inactivos: para ellos se solicita `activo=false`. Orden estable por `created_at,id`. GET por id permite consultar inactivos para administración. El repositorio combina SELECT acotado y COUNT con idéntico filtro. No devolver ORM sin schema.

### D-02 — Schemas alineados con persistencia

- Sillón: `consultorio_id` UUID existente y activo al crear o reasignar; `nombre` no vacío tras strip, máximo 80; `activo` opcional para activar/desactivar.
- Tratamiento: nombre máximo 120 no vacío; `duracion_min` entero estricto positivo hasta límite INTEGER; `precio_referencia_centavos` entero estricto nullable entre 0 y 2147483647. Mantener nombre explícito en centavos, sin alias ambiguo en pesos. Rechazar float y booleano como dinero/duración.
- Bloqueo: `sillon_id` UUID nullable; un sillón específico debe existir y estar activo al asignarlo; `desde/hasta` timezone-aware, `hasta>desde`; motivo no vacío, máximo 120. Validar el rango resultante después de fusionar PATCH con estado actual.
- Rechazar campos desconocidos. PATCH omite campos no enviados, permite null solo en campos nullable y rechaza null en requeridos. No admitir cambio de id ni metadatos.

### D-03 — Baja lógica y conservación histórica

DELETE conserva filas y FKs: `is_active=false`, `deleted_at=now(UTC)`. Desactivación por PATCH mantiene la misma semántica; reactivación limpia `deleted_at`. Repetir DELETE de un recurso existente inactivo devuelve 204 sin duplicar eventos si no hay cambio. Actualizar duración de tratamiento no recalcula turnos ya creados; fin histórico se preserva. No se modifica el EXCLUDE ni se habilitan sobreturnos aquí.

### D-04 — Advertencias de bloqueos

Al crear o modificar un bloqueo activo, consultar turnos `is_active=true`, estado no cancelado/ausente, `inicio < hasta AND fin > desde`; si sillón es null considerar todos. Rango semiabierto evita advertir por turnos adyacentes. Devolver en la respuesta del bloqueo `warnings: [{code: "TURNOS_SOLAPADOS", cantidad: N}]`, o lista vacía. Persistir normalmente; no cambiar ni cancelar turnos. Una consulta agregada no expone pacientes ni carga listas completas. Esto avisa sobre el estado observado, no garantiza exclusión transaccional contra reservas futuras: C-05 hará cumplir disponibilidad.

### D-05 — Auditoría durable y transaccional

Crear `ConfigAudit` / tabla `config_audit`: id UUID, `actor_id` FK Usuario no nulo, `recurso` (sillon/tratamiento/bloqueo), `recurso_id` UUID, `accion` (crear/actualizar/desactivar/reactivar), `created_at TIMESTAMPTZ`, `antes`/`despues` JSONB nullable según operación. CHECKs para recurso/acción; índices `(recurso,recurso_id,created_at)` y `(actor_id,created_at)`. Serializar solo campos de catálogo permitidos, UUID a string, fechas ISO con offset y centavos como enteros; no credenciales ni datos de pacientes. Los snapshots permiten conocer el cambio sin modificar AuditMixin global ni duplicar columnas por entidad. No ofrecer CRUD público de auditoría ni soft delete sobre eventos.

Mutación, flush, inserción de evento y commit pertenecen a una UoW: si falla auditoría, rollback completo. El actor sale de la dependencia autenticada, el tiempo del servidor/DB. Los timestamps del recurso y evento quedan timezone-aware. No usar logging de texto como sustituto de persistencia.

### D-06 — Migración y pruebas

Agregar revisión Alembic 002 dependiente de 001 que crea solo config_audit, checks e índices; downgrade elimina solo esa tabla. Mantener import de modelo para metadata y limpieza de tests. Probar upgrade/downgrade/upgrade exclusivamente en `turnos_test`, con autorización del entorno de test y nunca sobre datos de desarrollo que deban conservarse.

TDD cubre CRUD de los tres recursos y todas las operaciones por rol; validaciones, PATCH combinado, filtros/paginación, histórico intacto, bloqueos generales/específicos y bordes adyacentes. Probar auditoría de autor/acción/snapshots y rollback forzando fallo del evento. Verificar contrato de auth sin reemplazarlo por mocks permisivos; factory de sesiones aisladas en tests. Guardian estático y comprobación de catálogo PostgreSQL (MCP read-only si disponible; conexión de test como alternativa) verifican EXCLUDE, TIMESTAMPTZ y centavos.

## Risks / Trade-offs

- [Auditoría añade persistencia nueva] → migración mínima, campos allowlist y transacción conjunta.
- [Bloqueo coincide con turno existente] → advertencia explícita, sin borrar el turno; disponibilidad futura se resolverá en C-05.
- [Consultas administrativas de inactivos] → filtro explícito y GET por id; no esconder historial.
- [Fuente de datos modificada concurrentemente] → validar FKs y capturar IntegrityError con rollback y error de negocio; el motor conserva integridad.

## Migration Plan

1. Cerrar y archivar seguimiento de C-03 antes de Apply C-04.
2. Ejecutar migración 002 y suite sobre `turnos_test`; verificar preservación del esquema núcleo.
3. Registrar router y validar contratos OpenAPI, permisos y datos ficticios.
4. Tras revisión del usuario, sincronizar `agenda/catalogo-config`, archivar C-04 y marcarlo completo en CHANGES.md.
5. Rollback de aplicación puede dejar tabla audit intacta; downgrade destructivo solo en test o por operación explícita que acepte perder esa auditoría.
