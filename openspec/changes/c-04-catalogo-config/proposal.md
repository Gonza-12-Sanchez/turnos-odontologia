# Proposal — C-04 Catálogo y configuración

## Why

Los modelos de sillones, tratamientos y bloqueos existen desde C-02, pero no hay endpoints para configurarlos. C-04 habilita la administración del consultorio por secretaria y proporciona el catálogo que requiere C-05, respetando la dependencia de autenticación C-03.

## What Changes

- Agregar CRUD bajo `/api/config/sillones`, `/api/config/tratamientos` y `/api/config/bloqueos`, exclusivamente para secretaria.
- Exponer paginación uniforme, filtro de activos y validación tipada; montos enteros en centavos ARS y fechas con zona horaria.
- Desactivar mediante baja lógica, conservando turnos y relaciones históricas.
- Permitir bloqueos generales (`sillon_id=null`) y específicos; advertir sobre turnos existentes solapados sin impedir guardar el bloqueo.
- Persistir quién/cuándo/qué cambió en cada mutación, dentro de la misma transacción del catálogo.
- Verificar permisos por recurso y operación, invariantes PostgreSQL y rollback de auditoría con tests.

## Capabilities

### New Capabilities

- `agenda/catalogo-config`: administración de sillones, tratamientos y bloqueos, con acceso exclusivo para secretaria, paginación, baja lógica y auditoría.

### Modified Capabilities

Ninguna: reutiliza los invariantes vigentes de `core/models` y las dependencias de `identity/auth`.

## Impact

Nuevos schemas, repositorios, servicio y router de configuración en `backend/app/`; modelo y migración para auditoría de configuración; tests de API y persistencia. Los modelos de catálogo actuales se reutilizan. C-03 ya está archivado, pero su seguimiento correctivo debe verificarse y archivarse antes de implementar C-04. No implementa disponibilidad, reservas, sobreturnos, integraciones ni UI; esos comportamientos conservan sus changes del roadmap.
