# Tasks

## 1. Refactor GestionTurnosService para webhook (sin usuario autenticado)

- [x] 1.1 Cambiar firmas de `confirmar` y `cancelar` a `actor=None, origin=None` y omitir permisos/ownership cuando `actor is None`, manteniendo la ventana de 2 h y las transiciones; verificar que `tests/test_gestion_turnos.py` sigue verde.
- [x] 1.2 Agregar `origin` por defecto `whatsapp` cuando se invoca desde webhook y persistir `origen='whatsapp'`; verificar con test que un cambio por webhook deja `origen='whatsapp'`.

## 2. Abstracción de proveedor WhatsApp + mock

- [x] 2.1 Crear `backend/app/services/whatsapp_provider.py` con interfaz `WhatsAppProvider` (`send_template`) e implementaciones `MockProvider` y `MetaCloudProvider` (httpx); verificar import y que `MockProvider.send_template` devuelve un `message_id` determinista.
- [x] 2.2 Agregar selector `get_whatsapp_provider()` basado en `settings.whatsapp_provider` (vacío/mock → MockProvider); verificar con tests unitarios que la selección respeta env.
- [x] 2.3 Documentar costo/mensaje y proveedor elegido en `docs/whatsapp-cost.md` (o sección del design) con rango USD 0.005–0.015 y nota IN-10-02/04.

## 3. Servicio de RecordatorioWA

- [x] 3.1 Crear `backend/app/services/recordatorio_wa_service.py` con `registrar_envio(turno_id, plantilla, message_id, estado)` y `registrar_respuesta(message_id, respuesta, turno_id=None)` idempotente; verificar tests unitarios de creación y actualización.
- [x] 3.2 Implementar búsqueda de `RecordatorioWA` por `message_id` y por `turno_id`; verificar que retorna `None` si no existe.

## 4. Worker Redis (consumidor + reintentos)

- [x] 4.1 Crear `backend/app/workers/whatsapp_worker.py` con loop async `BRPOP wa:reminders`, procesamiento por turno, persistencia de envío y reencolado con backoff exponencial (máx. 5 intentos); verificar que un job feliz envía y persiste `enviado`.
- [x] 4.2 Implementar manejo de fallo del proveedor: persistir `fallido`, reencolar hasta el máximo y luego detener; verificar test que proveedor caído deja turno creado + reintento pendiente.
- [x] 4.3 Agregar `backend/app/workers/__main__.py` (o entrypoint `python -m app.workers.whatsapp_worker`) y documentar en README; verificar arranque manual sin errores de import.

## 5. Webhook firmado e idempotente

- [x] 5.1 Crear `backend/app/api/webhooks.py` con `POST /webhooks/whatsapp` (sin prefix o prefix `/webhooks`) que verifique firma HMAC-SHA256 (`X-Hub-Signature-256`) con `settings.whatsapp_api_key`, omitiendo solo en modo mock sin key; verificar 401 con firma inválida.
- [x] 5.2 Implementar idempotencia por `message_id` (Redis `SETNX` + consulta DB) y responder 200 en duplicado sin efectos; verificar test de `message_id` duplicado.
- [x] 5.3 Matchear turno vía `RecordatorioWA.message_id`; llamar a `GestionTurnosService.confirmar/cancelar` con `origin='whatsapp'` según `confirmo/cancelo`; verificar test `confirmo` confirma turno.
- [x] 5.4 Validar ventana de 2 h en `cancelo`: si falla, responder 422 con mensaje "Llamar al consultorio para cancelar" y dejar turno sin cambios; verificar test `cancelo` < 2 h rechazado.
- [x] 5.5 Registrar respuesta en `RecordatorioWA` (crear si no existe, tipo `confirmacion`) con `respuesta` y estado `respondido`; verificar persistencia en tests.

## 6. Cableado y configuración

- [x] 6.1 Registrar `webhooks_router` en `backend/app/main.py` (prefix `/webhooks` o raíz) y verificar que `POST /webhooks/whatsapp` está disponible (test de ruta).
- [x] 6.2 Agregar env vars a `.env.example` (`WHATSAPP_TEMPLATE_NAME`, opcional `WHATSAPP_WEBHOOK_SECRET`) y verificar que settings las carga.
- [x] 6.3 Modificar `reserva_service.py` para que el enqueue incluya solo `turno_id` (ya lo hace) y no falle si Redis cae (ya lo hace); verificar test de reserva con Redis caído no invalida turno.

## 7. Tests de integración (escenarios CHANGES)

- [x] 7.1 Test: reserva genera job en `wa:reminders` (verificar `LLEN`/`RPOP`).
- [x] 7.2 Test: webhook `confirmo` confirma turno end-to-end.
- [x] 7.3 Test: webhook `cancelo` < 2 h → 422 con mensaje.
- [x] 7.4 Test: `message_id` duplicado → idempotente.
- [x] 7.5 Test: proveedor caído → turno creado + reintento pendiente.

## Workflow follow-up

- Archive the change after review requirements are satisfied.
- Verify the archived result.
