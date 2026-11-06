# Proposal — C-08 WhatsApp Notificaciones

## Why

C-06 completa el ciclo de vida del turno, pero la notificación automática por WhatsApp (RN-NT-01/02/03) y la confirmación/cancelación vía webhook (Flujo 2) no existen: la reserva solo encola un `turno_id` en Redis (`wa:reminders`) sin consumidor, y no hay endpoint para recibir la respuesta del paciente. C-08 cierra la integración obligatoria del MVP v1 para reducir inasistencias.

## What Changes

- Worker Redis (`backend/app/workers/`) que consume la lista `wa:reminders`, envía recordatorio por plantilla Meta para cada turno, con reintentos con backoff; si el proveedor falla, el turno existe igual y se reencola el job (RN-NT-03, Flujo 1 caso de error).
- `POST /webhooks/whatsapp`: recibe `confirmo|cancelo` + `message_id`; idempotencia por `message_id`; matchea el turno, valida ventana de 2 h si es cancelación (RN-TU-02 → rechazo con mensaje "llamar al consultorio"), actualiza estado vía `GestionTurnosService` y registra la respuesta en `RecordatorioWA` (RN-NT-02/03).
- Verificación de firma del webhook; credenciales solo por env (`WHATSAPP_PROVIDER`, `WHATSAPP_API_KEY`).
- Abstracción de proveedor con mock para tests (IN-10-02) y registro del costo/mensaje en docs del change.
- Persistencia de envíos/respuestas en `RecordatorioWA` (tipo, plantilla, `message_id`, estado, respuesta).
- Tests: reserva genera job WA; webhook `confirmo` confirma turno; `cancelo` < 2 h → rechazado; `message_id` duplicado → idempotente; proveedor caído → turno creado + reintento pendiente.

## Capabilities

### New Capabilities

- `platform/whatsapp-notificaciones`: envío de recordatorios por plantilla Meta mediante worker Redis con reintentos, recepción idempotente de respuestas del paciente vía webhook firmado, actualización de estado del turno y registro en `RecordatorioWA`.

### Modified Capabilities

Ninguna: reutiliza los invariantes vigentes de `core/models`, `identity/auth`, `agenda/disponibilidad-reserva` y `agenda/gestion-turnos`. El enqueue ya está en C-05 y el origen `whatsapp` ya está contemplado en `agenda/gestion-turnos`.

## Impact

Nuevos módulos en `backend/app/workers/`, `backend/app/api/webhooks.py`, `backend/app/services/whatsapp_provider.py` (abstracción + mock), `backend/app/services/recordatorio_wa_service.py`; consumo de `GestionTurnosService`; firma HMAC del webhook; tests de API, worker e idempotencia; documentación de costo/mensaje y elección de proveedor. Sin cambios de modelos ni migraciones. Sin UI.