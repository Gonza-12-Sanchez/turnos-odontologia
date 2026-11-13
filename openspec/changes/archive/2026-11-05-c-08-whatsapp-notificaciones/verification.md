# C-08 — Verificación de notificaciones WhatsApp

## Estado
Archivado 2026-11-05 (23/23 tasks, suite backend 262 passed, 1 fallo preexistente test_auth).

## Evidencia
- Worker Redis (`backend/app/workers/`): al reservar (evento C-05) agenda recordatorio por plantilla Meta; reintentos con backoff; si falla el proveedor, el turno existe igual + reintento encolado.
- `POST /webhooks/whatsapp`: recibe `confirmo|cancelo` + `message_id`; idempotencia por `message_id`; matchea turno, valida ventana 2 h si es cancelación (RN-TU-02 → rechazo con mensaje), actualiza estado + registra respuesta en `RecordatorioWA`.
- Firma del webhook verificada; credenciales solo por env (`WHATSAPP_PROVIDER`, `WHATSAPP_API_KEY`).
- Proveedor a elegir o mock para Etapa 6 (IN-10-02).

## Tests
- Reserva genera job WA.
- Webhook `confirmo` confirma turno.
- `cancelo` < 2 h → rechazado.
- `message_id` duplicado → idempotente.
- Proveedor caído → turno creado + reintento pendiente.

## Guardian
N/A (integración externa, no modelos críticos de motor).
