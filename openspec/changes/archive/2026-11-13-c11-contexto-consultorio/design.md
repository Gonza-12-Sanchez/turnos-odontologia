# Design

## Context

`Consultorio` tiene id, nombre y estado activo; `Usuario` no tiene pertenencia a
consultorio. El alcance MVP documentado en CHANGES.md es una sede y el router
`/api/config` ya restringe operaciones a secretaria. Ver proposal y spec delta.

## Goals / Non-Goals

**Goals:** exponer un contexto inequívoco para el primer sillón con el menor
cambio compatible con el RBAC existente.

**Non-Goals:** multi-sede, inferir pertenencias por usuario, crear consultorios,
modificar modelos/migraciones o cambiar la semántica del POST existente.

## Decisions

- GET `/api/config/contexto-consultorio`: respuesta 200 `{consultorio: {id,
  nombre} | null}`; consultar hasta dos consultorios activos, devolver uno solo
  si el resultado contiene exactamente uno. Cero o más de uno da null, sin
  escoger la primera fila. Errores de base no son equivalentes a null.
- Aplicar el mismo `require_admin()` que el router, conservando401/403; limitar
  salida a id/nombre y no cachear. La UI C-11 validará el DTO runtime y dejará
  el alta bloqueada si falta contexto, sin UUID manual ni inferencia de sillones.
- Alternativa rechazada: elegir cualquier consultorio o asignar relación usuario
  sin fuente real. El supuesto de sede única viene de CHANGES.md; si se requiere
  multi-sede, se necesitará asignación y autorización explícitas antes de habilitarlo.
- Pruebas API con cliente HTTP y Postgres/Redis descartables nuevos para autorización
  real, cero/uno/dos activos y POST primer sillón; fixtures existentes truncan
  tablas, por lo que nunca se apuntan a localhost existente. HTTP/DOM simulado
  solo para los estados frontend. Sin pagos ni datos reales.

## Risks / Trade-offs

- [Sede única no equivale a multi-tenant] → fallar cerrado ante múltiples activos;
  no presentar este endpoint como autorización de una futura instalación multi-sede.
- [Cambio entre lectura y POST] → POST ya verifica existencia y actividad; probar
  condición cambiante. El contrato existente no garantiza unicidad frente a alta
  concurrente de otra sede; no declarar soporte multi-sede.

## Migration Plan

Desplegar backend antes de la UI; cliente anterior no cambia. Si falta endpoint,
la UI muestra indisponibilidad y no crea sillones. Rollback de la UI o endpoint
no elimina datos. Sin migraciones.

## UI Mockups

Decision: no (no UI). Este correctivo solo define backend; C-11 posee mockups
aprobados para el alta y mantiene su propia verificación visual.

El delta de este correctivo amplía la especificación canónica de [configuración de agenda](../../../specs/agenda/catalogo-config/spec.md).
