# Funcionalidades

Organizadas por **épica** y luego por **historia de usuario** (formato US-NNN). Trazabilidad a `05_reglas_de_negocio.md`.

## Épica 1: Reserva online (Paciente)

### US-001 — Ver horarios libres
**Como** paciente **Quiero** ver horarios libres por fecha/sillón/tratamiento sin login **Para** elegir cuándo reservar sin escribir por WhatsApp.

**Criterios de aceptación**:
- [ ] Muestra franjas reales según sillones activos, duración del tratamiento y bloqueos.
- [ ] No muestra franjas ocupadas ni bloqueadas.
- [ ] Funciona en celular (PWA mobile-first).

**Reglas relacionadas**: RN-TU-03, RN-TU-04, RN-TU-06.

### US-002 — Reservar turno con login
**Como** paciente logueado **Quiero** reservar un horario libre **Para** asegurar mi cita 24/7.

**Criterios de aceptación**:
- [ ] Exige login (RN-AU-01); anónimo no puede reservar.
- [ ] Rechaza la reserva si el hueco se ocupó entre la consulta y la confirmación (RN-TU-01).
- [ ] Si el tratamiento exige seña, redirige a Mercado Pago y reserva al aprobarse el pago (RN-CO-01).

**Reglas relacionadas**: RN-AU-01, RN-TU-01, RN-TU-03, RN-CO-01.

### US-003 — Ver Mis reservas
**Como** paciente **Quiero** ver mis reservas asignadas **Para** controlar mis citas.

**Criterios de aceptación**:
- [ ] Lista solo turnos propios, ordenados por fecha, con estado y tolerancia visible.
- [ ] Permite confirmar/cancelar respetando RN-TU-02.

**Reglas relacionadas**: RN-TU-02, RN-TU-05.

## Épica 2: Agenda del consultorio (Odontólogo / Secretaria)

### US-004 — Ver agenda del día
**Como** odontólogo **Quiero** ver mi agenda del día **Para** saber cuántos pacientes tengo y a qué hora.

**Criterios de aceptación**:
- [ ] Vista día por sillón con paciente, tratamiento, estado y tolerancia.
- [ ] Aviso visual de sobreturnos y de solapamientos intentados.

**Reglas relacionadas**: RN-TU-01, RN-TU-04, RN-TU-05, RN-TU-06.

### US-005 — Confirmar / cancelar / reprogramar (secretaria)
**Como** secretaria **Quiero** confirmar/cancelar/reprogramar turnos **Para** mantener la agenda real.

**Criterios de aceptación**:
- [ ] Cancelar/reprogramar bloqueado si faltan < 2 h (RN-TU-02), también para secretaria.
- [ ] Reprogramar revalida disponibilidad y anti-solapamiento.
- [ ] Todo cambio queda auditado (RN-GL-03).

**Reglas relacionadas**: RN-TU-01, RN-TU-02, RN-GL-03.

## Épica 3: Notificaciones WhatsApp

### US-006 — Recordatorio automático con botón
**Como** sistema **Quiero** enviar recordatorio por WhatsApp con botón confirmar/cancelar **Para** reducir inasistencias sin trabajo manual.

**Criterios de aceptación**:
- [ ] Se envía por plantilla Meta; se registra entrega (RN-NT-03).
- [ ] La respuesta del paciente actualiza el turno; cancelar respeta RN-TU-02.

**Reglas relacionadas**: RN-NT-01, RN-NT-02, RN-NT-03, RN-TU-02.

## Épica 4: Cobros simples

### US-007 — Cobrar y asignar turnos en local
**Como** secretaria **Quiero** cobrar (efectivo/transferencia/MP) y asignar turnos **Para** cerrar el circuito en el local.

**Criterios de aceptación**:
- [ ] Cobro registrado contra el turno en centavos ARS.
- [ ] Sin factura electrónica en v1 (explícito en UI si se intenta).

**Reglas relacionadas**: RN-CO-02, RN-CO-03.
