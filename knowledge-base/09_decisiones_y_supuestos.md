# Decisiones y Supuestos

## Decisiones documentadas

### DD-01 — v1 es solo turnos, sin HCE ni ARCA
**Decisión**: el MVP cubre reserva + agenda + WhatsApp + cobro simple; ARCA va en fase 2 y OOSS/HCE en fase 3+.
**Contexto**: el top-5 de competidores ya cubre todo integrado; el vacío es simplicidad + precio.
**Alternativas consideradas**: (a) clon funcional de Denteo/Oclusar; (b) solo agenda sin notificaciones.
**Justificación**: informe-discovery §C3/D — diferenciar por ejecución de lo básico, no por módulos.
**Trade-offs aceptados**: sin facturación legal en v1; consultorios que exijan ARCA día 1 no son cliente inicial.

### DD-02 — Multi-sillón y duración variable desde día 1
**Decisión**: sillón obligatorio por turno y duración por tratamiento (RN-TU-03/04).
**Contexto**: es el gap detectado vs. coordinar por WhatsApp y vs. OdontoApp.
**Alternativas**: turno de duración fija. **Justificación**: los tratamientos reales varían (15–60 min); sin esto la agenda miente.
**Trade-offs**: disponibilidad más compleja de calcular.

### DD-03 — WhatsApp como única integración obligatoria v1
**Decisión**: recordatorio + confirmación automáticos con botón vía plantillas Meta (RN-NT-*).
**Alternativas**: SMS/email. **Justificación**: es el canal que ya usan consultorio y paciente; ataca inasistencias.
**Trade-offs**: costo por mensaje (ver IN-10-04) y riesgo de bloqueo por spam (riesgo heredado de Discovery).

### DD-04 — Login obligatorio para reservar
**Decisión**: ver libres es público; reservar exige paciente logueado (RN-AU-01).
**Alternativas**: reserva anónima con teléfono. **Justificación**: trazabilidad de Mis reservas y anti-abuso.
**Trade-offs**: fricción en la reserva — esquema a decidir (IN-10-03).

### DD-05 — Invariantes a nivel de motor
**Decisión**: anti-solapamiento y ventana de 2 h como constraints de backend, nunca solo UI (RN-GL-01).
**Justificación**: la doble reserva es el dolor central; la UI sola no lo garantiza.

### DD-06 — Stack: FastAPI + React/TS/Vite + Postgres + Redis + Docker
**Decisión** (2026-10-06, equipo): backend Python + FastAPI (JWT, SQLAlchemy 2.x async), PostgreSQL 16+, Redis 7+ para lo asincrónico, Docker/Docker Compose; frontend React + TypeScript + Vite (PWA).
**Contexto**: Discovery dejaba libertad total de stack (IN-10-01); roadmap y Etapa 6 lo necesitan fijo.
**Alternativas consideradas**: backend Node o monolito sin Redis; frontend SSR.
**Justificación**: FastAPI + Pydantic modela bien las invariantes RN-TU-*; Postgres aporta exclusión por rango para RN-TU-01; Redis desacopla WhatsApp/webhooks; Vite + TS agiliza la PWA.
**Trade-offs aceptados**: dos runtimes (Node para build + Python para API) y un servicio extra (Redis) en Compose.

## Supuestos inferidos

### SU-01 — Los pacientes prefieren reservar online antes que WhatsApp
**Supuesto**: la reserva web es más fácil que escribir por WhatsApp. **Origen**: informe §C3 (declarado como supuesto sin probar).
**Riesgo si es falso**: baja adopción del canal online. **Cómo validar**: piloto con 1 consultorio midiendo % online vs WhatsApp.

### SU-02 — La agenda se mantiene al día
**Supuesto**: secretaria/odontólogo cargan bloqueos y estados. **Origen**: discovery riesgo 2.
**Riesgo si es falso**: libres falsos. **Cómo validar**: alertas de turnos sin confirmar + reporte de higiene de agenda.

### SU-03 — El costo de WhatsApp es asumible
**Supuesto**: el consultorio absorbe el costo por mensaje. **Origen**: discovery riesgo 3/4.
**Riesgo si es falso**: feature apagada = vuelven las inasistencias. **Cómo validar**: definir quién paga antes del piloto (IN-10-04).
