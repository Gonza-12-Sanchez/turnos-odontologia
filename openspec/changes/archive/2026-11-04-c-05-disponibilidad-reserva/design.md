# Design — C-05 Disponibilidad y reserva

## Context

Ver `proposal.md` para motivación. Los modelos `Turno`, `Sillon`, `Tratamiento`, `Bloqueo` y `Paciente` existen con AuditMixin, TIMESTAMPTZ, centavos y el EXCLUDE de motor. C-04 expone catálogo y bloqueos. No hay código previo de disponibilidad ni de reserva. Redis ya está integrado para cache y colas.

## Goals / Non-Goals

**Goals:** calcular franjas libres públicas por tratamiento y sillón, reservar con validación de hueco y anti-solapamiento de motor, manejar carrera concurrente, devolver alternativas en conflicto, contrato de seña (402) y enqueue de recordatorio WhatsApp, con cache Redis invalidado al reservar.

**Non-Goals:** máquina de estados del turno (C-06), endpoints de lectura de agenda/mis reservas (C-07), worker WhatsApp (C-08), cobro MP/webhook (C-09), UI (C-10/C-11).

## Decisions

### D-01 — Rutas y permisos

Router sin prefijo (`/horarios-libres`, `/turnos`) registrado en `main.py`. `GET /horarios-libres` es público (sin auth). `POST /turnos` exige `require_role("paciente")`. El paciente se resuelve desde el token hacia `Paciente` (1↔1).

### D-02 — Algoritmo de disponibilidad

Para la fecha solicitada (día UTC) y el tratamiento, para cada sillón activo (filtrado si se envía `sillon`):
- generar candidatos desde `00:00` hasta `24:00` con paso `duracion_min` del tratamiento;
- descartar candidatos que se solapen con un turno activo (`is_active=true`, estado no cancelado/ausente) o con un bloqueo activo (general o del sillón), usando rango semiabierto `inicio < bloqueo.hasta AND fin > bloqueo.desde`;
- devolver `{sillon_id, inicio, fin}` ordenado por sillón y inicio.

No se exponen datos de paciente. El tratamiento debe estar activo; si no, 422.

### D-03 — Cache Redis

Clave `avail:{fecha}:{tratamiento_id}:{sillon or all}`, TTL 60 s. Al crear un turno se eliminan las claves `avail:{fecha}:*` para esa fecha (scan). En tests se usa el cliente namespaced existente.

### D-04 — Flujo de reserva

1. Resolver paciente desde el usuario autenticado.
2. Validar sillón y tratamiento activos (404 si no existen, 422 si inactivos).
3. Parsear `inicio` como AwareDatetime; calcular `fin = inicio + duracion_min` en servidor (rechazar `fin` del cliente).
4. Verificar disponibilidad a nivel aplicación; si no hay hueco, responder 409 con `alternativas` (primeras 3 franjas libres del mismo día/tratamiento).
5. Si el payload o tratamiento indican seña requerida, responder 402 con datos de checkout y no persistir.
6. Crear `Turno` (`estado=reservado`, `origen=online`, `es_sobreturno=false`) dentro de una UoW.
7. Capturar `IntegrityError` (EXCLUDE) → rollback, responder 409 con alternativas.
8. Commit, invalidar cache, encolar job de recordatorio WhatsApp en Redis (`LPUSH wa:reminders <turno_id>`). Si el enqueue falla, loguear y no invalidar la reserva (RN-NT-03).

### D-05 — Respuesta de conflicto

Toda respuesta 409 incluye `detail` y `alternativas: [{sillon_id, inicio, fin}]`.

### D-06 — Validaciones

`inicio` debe ser timezone-aware (AwareDatetime) → 422 si naive. Montos no se manejan aquí (centavos en C-09).

## Risks / Trade-offs

- [Ventana diaria 24 h sin horario comercial configurado] → asumido; puede refinarse con settings en C-12. No hay regla de negocio que defina horario.
- [Paso de candidatos = duración] → puede omitir inicios intermedios; aceptable para MVP y consistente con "expandiendo por duracion_min".
- [Cache por fecha completa] → invalidación por scan; aceptable en escala de consultorio.
- [Seña por payload/tratamiento] → contrato mínimo; C-09 completará preferencia MP y webhook.

## Migration Plan

1. No requiere migración nueva (reutiliza esquema 001/002).
2. Registrar router en `main.py`.
3. Ejecutar suite sobre `turnos_test`; verificar concurrencia.
4. Tras revisión, sincronizar spec `agenda/disponibilidad-reserva`, archivar y marcar C-05 completo.