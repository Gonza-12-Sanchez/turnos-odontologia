# Proposal — C-05 Disponibilidad y reserva

## Why

C-04 ya expone el catálogo (sillones, tratamientos, bloqueos), pero todavía no hay forma de calcular franjas libres ni de reservar un turno. C-05 introduce la capacidad central del MVP: disponibilidad real por tratamiento y reserva con invariantes de motor, incluyendo carrera concurrente y contrato de seña para C-09.

## What Changes

- Agregar `GET /horarios-libres` público (sin login) que calcula franjas reales = sillones activos − turnos activos − bloqueos, expandiendo por `duracion_min` del tratamiento; sin exponer datos de pacientes; cache Redis TTL corto con invalidación al crear turno.
- Agregar `POST /turnos` que requiere login paciente (RN-AU-01): valida el hueco, calcula `fin = inicio + duracion`, verifica anti-solapamiento a nivel motor antes de confirmar (RN-TU-01, RN-GL-01); carrera por el mismo hueco → `409 + oferta de alternativas`.
- Si el tratamiento exige seña (precio de referencia), responder `402 + checkout MP` y NO crear el turno hasta webhook aprobado (contrato RN-CO-01, implementado en C-09).
- Encolar el recordatorio WhatsApp al reservar (evento/cola Redis, RN-NT-01); el worker se implementa en C-08, aquí solo el enqueue.
- Tests: libres excluyen ocupados y bloqueados; reserva sin login 401; doble reserva concurrente → una 201 + otra 409; duración variable genera fin correcto; tratamiento con seña sin pago → turno no creado.

## Capabilities

### New Capabilities

- `agenda/disponibilidad-reserva`: cálculo público de horarios libres por tratamiento y reserva de turno con validación de hueco, anti-solapamiento de motor, carrera concurrente, cache Redis y contrato de seña/WhatsApp.

### Modified Capabilities

Ninguna: reutiliza los invariantes vigentes de `core/models` (EXCLUDE, TIMESTAMPTZ, centavos) y las dependencias de `identity/auth` y `agenda/catalogo-config`.

## Impact

Nuevos schemas, repositorio/servicio de disponibilidad y reserva, router público en `backend/app/`; cache Redis de libres; integración con `Tratamiento`, `Sillon`, `Bloqueo`, `Turno`, `Paciente`; pruebas de API y concurrencia. No implementa gestión de estados (C-06), lectura de agenda (C-07), notificaciones (C-08), cobros (C-09) ni UI (C-10/C-11).