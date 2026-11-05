# Visión y Objetivos

> Fuente: `docs/discovery/checklist-discovery.md` (2026-09-29) + `docs/discovery/informe-discovery.md` (2026-10-06). Modo ingest — sin preguntas.

## Propósito del sistema

Sistema de gestión de turnos y agenda de pacientes para consultorios odontológicos chicos de Argentina (1–3 sillones, 1 sede), que reemplaza la coordinación por WhatsApp/papel —origen de dobles reservas, tiempo perdido en confirmación manual e inasistencias sin recupero— por reserva online 24/7, agenda multi-sillón con anti-solapamiento y recordatorio/confirmación automáticos por WhatsApp.

## Objetivos por actor

| Actor | Objetivo principal | Objetivos secundarios |
|---|---|---|
| Paciente | Reservar online sin escribir por WhatsApp | Ver sus reservas asignadas; confirmar/cancelar; llegar a tiempo (tolerancia visible) |
| Odontólogo / dueño | Ver su agenda del día | Evitar dobles reservas y huecos por inasistencia |
| Secretaria | Mantener la agenda real (confirmar/cancelar/reprogramar) | Cobrar y asignar turnos; cerrar el circuito en el local |

## Alcance v1

- Reserva online 24/7 (ver libres + reservar).
- Agenda diaria multi-sillón con anti-solapamiento, duración variable por tratamiento, bloqueos y sobreturnos.
- Confirmación / cancelación / reprogramación (paciente + secretaria), con cancelación mínima de 2 h bloqueada por sistema.
- Mis reservas para paciente logueado.
- Recordatorio + confirmación WhatsApp automático con botón (única integración obligatoria v1).
- Registro de cobro simple en local + asignación de turnos.
- Roles paciente / odontólogo / secretaria, 1 sede, PWA mobile-first.
- Seña por Mercado Pago opcional y políticas auto-ejecutadas.

## Fuera de alcance

- Facturación electrónica ARCA (fase 2, modelo listo, no bloquea v1).
- Obras sociales y liquidaciones (fase 3).
- Odontograma / HCE completa, ortodoncia, imágenes (fase 3+).
- Marketplace, campañas / recuperación de ausentes, IA, multi-sede, API pública, GCal bidireccional.
- Pagos online avanzados, membresías / giftcards, loyalty.

## Métricas de éxito

- Cero dobles reservas mismo sillón/horario (RN-TU-01).
- Inasistencias con recordatorio automático < inasistencias coordinadas por WhatsApp manual (a medir contra línea base del consultorio).
- 100 % de turnos v1 con estado trazable (reservado → confirmado → asistido / cancelado).
- Tiempo de secretaria en confirmación manual tendiendo a cero.
