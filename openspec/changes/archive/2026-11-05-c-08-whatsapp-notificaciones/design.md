# Design — C-08 WhatsApp Notificaciones

## Context

See `proposal.md` — Why. La reserva (C-05) ya encola `turno_id` en la lista Redis `wa:reminders`; `RecordatorioWA` y sus constraints existen (C-02); `GestionTurnosService` (C-06) gestiona estados con ventana de 2 h y origen auditable. C-08 consume esa cola, envía la plantilla Meta y recibe la respuesta del paciente. No hay cambios de modelo ni migración.

## Goals / Non-Goals

**Goals:** worker consumidor con reintentos/backoff y reencolado; abstracción de proveedor con mock; webhook firmado e idempotente por `message_id`; actualización de estado vía `GestionTurnosService` con origen `whatsapp`; persistencia en `RecordatorioWA`; tests TDD de los 5 escenarios del CHANGES.

**Non-Goals:** elección definitiva de proveedor real (IN-10-02) — se deja pluggable y se usa mock en Etapa 6; UI; migraciones; métricas de entrega del proveedor (entregado/leído se actualizan por webhook de estado si el proveedor lo envía, pero no es requisito MVP); cobro de mensajes (IN-10-04).

## Decisions

### D-01 — Abstracción de proveedor
Interfaz `WhatsAppProvider` con `async def send_template(turno, plantilla) -> str` (devuelve `message_id`). Implementaciones: `MetaCloudProvider` (httpx, real) y `MockProvider` (tests). Selección por `settings.whatsapp_provider`: vacío o `mock` → `MockProvider`; otro valor → proveedor real correspondiente. Credenciales solo por env (RN-GL-01 de seguridad).

### D-02 — Worker consumidor con reintentos
Loop async que hace `BRPOP wa:reminders` (timeout 5 s) y procesa cada `turno_id`. Intentos controlados por clave Redis `wa:reminder:attempts:{turno_id}` (TTL 1 h). Backoff exponencial `1,2,4,8,16` s (tope 60 s), máximo 5 intentos. Al agotar intentos se persiste `RecordatorioWA` con estado `fallido` y no se reencola. Errores de Redis no invalidan el turno (el job se descarta; la reserva ya confirmó). El worker se ejecuta como proceso separado (`python -m app.workers.whatsapp_worker`) y respeta el event loop (async puro).

### D-03 — Persistencia del envío
Al enviar con éxito se crea `RecordatorioWA(tipo='recordatorio', plantilla=<nombre>, message_id=<id>, estado='enviado')`. El nombre de plantilla se configura en env `WHATSAPP_TEMPLATE_NAME` (default `recordatorio_turno`). Al fallar se crea con estado `fallido` y `message_id=None`.

### D-04 — Idempotencia del webhook
Clave Redis `wa:webhook:msg:{message_id}` con `SETNX` + TTL 24 h. Si ya existe → responder 200 sin efectos. Además consulta `RecordatorioWA` por `message_id`; si existe y ya tiene respuesta → idempotente. Doble barrera (Redis + DB) para robustez.

### D-05 — Firma del webhook
HMAC-SHA256 del body crudo con secreto `settings.whatsapp_api_key` (o `WHATSAPP_WEBHOOK_SECRET` si se agrega; reutilizamos `whatsapp_api_key` para no tocar settings). Comparación con `hmac.compare_digest` contra header `X-Hub-Signature-256` (formato `sha256=<hex>`). Si `whatsapp_provider == 'mock'` y no hay key, se omite la verificación (solo en modo mock). En modo real sin key → 503.

### D-06 — Matcheo de turno y transiciones
El webhook busca `RecordatorioWA` por `message_id` para obtener `turno_id`. Llama a `GestionTurnosService.confirmar(turno_id, actor=None, origin='whatsapp')` o `cancelar(...)` según respuesta. Para soportar webhook sin usuario autenticado, `confirmar`/`cancelar` aceptan `actor=None` y omiten permisos/ownership en ese caso (decisión justificada: el webhook es un actor del sistema ya verificado por firma).

### D-07 — Ventana de 2 h en cancelación
Reutiliza `_window_ok`. Si falla → 422 con `detail="Llamar al consultorio para cancelar"` (mensaje para el paciente). El turno queda sin cambios. Se persiste intento en `RecordatorioWA` con respuesta `cancelo` y estado `respondido`? No — solo si la cancelación se aplicó. Si se rechaza, se registra estado `respondido` con respuesta `cancelo` pero sin cambiar el turno, y se devuelve el mensaje. (Audit: el intento queda registrado.)

### D-08 — Registro de respuesta
Al procesar `confirmo`/`cancelo` exitoso se actualiza el `RecordatorioWA` vinculado: `respuesta=<valor>`, `estado='respondido'`. Si no existe registro previo (webhook huérfano), se crea uno con `tipo='confirmacion'`, `plantilla=<config>`, `message_id=<id>`, `estado='respondido'`, `respuesta=<valor>`.

### D-09 — Concurrencia
El webhook es stateless; la idempotencia por `message_id` (D-04) cubre reintentos del proveedor. Las transiciones de turno usan la sesión/UnitOfWork existente; conflictos de concurrencia devuelven 409/422 estándar.

### D-10 — Costo y proveedor (docs)
Proveedor recomendado para Etapa 6: Meta Cloud API directa o un BSP (360dialog/Twilio) según disponibilidad de cuenta WABA. Costo estimado: USD 0.005–0.015 por mensaje de plantilla (varía por país/categoría; AR ~ USD 0.008). Se registra en este design y en `docs/whatsapp-cost.md` del change si se crea. Quién paga (IN-10-04) queda abierto para el piloto.

## Risks / Trade-offs

- [Webhook sin firma en mock] → solo en modo mock; en producción se exige firma y se rechaza sin key.
- [Worker bloquea event loop] → async puro con `asyncio.sleep` para backoff; sin trabajo síncrono pesado.
- [Duplicados por reintentos del proveedor] → idempotencia doble (Redis + DB).
- [Turno cancelado por otra vía entre envío y respuesta] → `GestionTurnosService` devuelve 422; se registra y se informa.
- [Costo no controlado] → monitoreo vía `RecordatorioWA` count; límite de reintentos evita tormentas.

## Migration Plan

1. No requiere migración (modelo existente).
2. Agregar endpoints y worker; registrar en `main.py`/router.
3. Configurar env vars en `.env.example` (ya existen `WHATSAPP_PROVIDER`, `WHATSAPP_API_KEY`; agregar `WHATSAPP_TEMPLATE_NAME`, `WHATSAPP_WEBHOOK_SECRET` opcional).
4. Ejecutar suite y ruff.
5. Rollback: revertir commit; la cola `wa:reminders` queda sin consumidor (reservas siguen funcionando; solo no se envían recordatorios).

## Open Questions

- IN-10-02: proveedor real definitivo — se resuelve con el consultorio piloto; la abstracción permite cambiar sin tocar dominio.
- IN-10-04: quién paga los mensajes — decisión de negocio, no bloquea implementación.

## UI Mockups

- Design system revision: n/a
- Decision: no (no UI) — 2026-11-05
- Mockups: n/a
- Approval: n/a
- Preview: n/a
- Visual verify: n/a

## Governance Checkpoints (ALTO)

- CP-1: firma del webhook verificada antes de procesar (security-and-hardening).
- CP-2: idempotencia por `message_id` validada por tests.
- CP-3: credenciales solo por env; sin secretos en repo (ruff/scan).
- CP-4: proveedor caído → turno creado + reintento pendiente (test).
- CP-5: cancelación < 2 h → rechazada con mensaje "llamar al consultorio" (test).
- CP-6: origen `whatsapp` persistido para auditoría (RN-GL-03).