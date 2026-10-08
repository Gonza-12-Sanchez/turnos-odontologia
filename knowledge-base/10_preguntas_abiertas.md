# Preguntas Abiertas

## Entradas de discovery (baja confianza, modo ingest)

[DISCOVERY] `system_type` — RESUELTA 2026-10-06: `web_app` (React SPA + FastAPI, ver DD-06).
[DISCOVERY] `stack` — RESUELTA 2026-10-06: backend Python + FastAPI + JWT + SQLAlchemy + PostgreSQL + Redis + Docker/Compose; frontend React + TypeScript + Vite (ver DD-06).
[DISCOVERY] `scale` es orientativo desde `usuarios` (paciente + equipo de 1 sede). Valor asentado: `public_multi_user (inferred, low confidence)`. Confirmar: ¿escala y multi-sede futura?

## Inconsistencias detectadas

### IN-10-01 — Stack sin definir en ninguna fuente — RESUELTA 2026-10-06
**Documento A dice** (README): requisitos Node 20+, Git, Go — pero corresponden al entorno Active Stack, no al stack de la app.
**Documento B dice** (discovery): "libertad total de stack".
**Resolución aplicada**: stack fijado por el equipo — backend Python + FastAPI + JWT + SQLAlchemy + PostgreSQL + Redis + Docker/Compose; frontend React + TypeScript + Vite (DD-06; `02` y `08` actualizados).

### IN-10-02 — Proveedor de WhatsApp sin elegir
**Discovery dice**: "vía proveedor plantillas Meta, costo por mensaje" sin nombrar proveedor.
**Impacto**: RN-NT-* no implementable sin proveedor + credenciales + costos.
**Resolución propuesta**: elegir proveedor (o mock para Etapa 6) y registrar costo/mensaje.

### IN-10-03 — Esquema de credential sin decidir
**Discovery dice**: "paciente con login" pero "re-evaluar password vs OTP-WhatsApp para no frenar reserva".
**Impacto**: RN-AU-02 y Flujo 1 cambian según la decisión.
**Resolución propuesta**: decidir antes del primer change (recomendación: password simple v1, OTP como mejora).

### IN-10-04 — Quién paga los mensajes de WhatsApp
**Discovery dice**: supuesto "costo mensajes sin presupuesto techo — quién lo paga debe definirse".
**Impacto**: modelo de negocio del piloto.
**Resolución propuesta**: definirlo con el consultorio piloto (SU-03).

## Preguntas abiertas (priorizadas)

| Prioridad | Pregunta | Bloquea | Decisor |
|---|---|---|---|
| Alta | ¿Password u OTP-WhatsApp para paciente? | Primer change (auth) | Equipo + UX |
| Alta | ¿Proveedor WhatsApp y quién paga? | Notificaciones | Product Owner |
| Media | 9+ sistemas sin nota individual, 1 guía de ayuda, 1 video/marketplace, 1 reseña independiente (pendientes del informe) | Rigor de KB v2 | Equipo |
| Media | ¿Seña obligatoria u opcional por tratamiento? | RN-CO-01 | Product Owner |
| Baja | ¿GCal bidireccional entra en fase 2 o 3? | Post-MVP | Product Owner |
