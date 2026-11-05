# Modelo de Datos

## Dominios

- **Agenda**: sillones, tratamientos (duración), turnos, bloqueos, sobreturnos.
- **Personas y acceso**: usuarios, roles, pacientes.
- **Comunicación**: recordatorios y confirmaciones por WhatsApp.
- **Cobros**: cobros locales y señas por Mercado Pago.

## ERD

```
Usuario(1)──<(Rol)            Paciente(1)──<Turno(*)──<(Cobro)
   │                              │              │
   │                              │              └──<RecordatorioWA(*)
Sillon(1)──<Turno(*)      Tratamiento(1)──<Turno(*)
Consultorio(1)──<Sillon(*) · <Bloqueo(*) · <Usuario(*)
```

- Un Turno ocupa un Sillón en [inicio, fin) — fin = inicio + duración del Tratamiento (RN-TU-03).
- Invariante: no existen dos Turnos activos solapados en el mismo Sillón (RN-TU-01).
- Bloqueo reserva franjas no reservables (feriados, almuerzo, mantenimiento).

## Entidades

### Usuario
- Atributos: id (uuid), email/teléfono (único), hash_password, rol (paciente|odontologo|secretaria), activo (bool), creado_en.
- Relaciones: 1 Usuario ↔ 0..1 Paciente (rol paciente); N Turnos atendidos (odontólogo).
- Constraints: rol NOT NULL; login obligatorio para reservar (RN-AU-01).
- Índices: (email), (rol, activo).

### Paciente
- Atributos: id, usuario_id (FK único), nombre, teléfono, obra_social (texto libre, solo informativo en v1), notas.
- Relaciones: 1 Paciente — N Turnos; N Cobros.
- Constraints: teléfono con formato AR validado a nivel app.

### Sillon
- Atributos: id, consultorio_id, nombre ("Sillón 1"), activo.
- Relaciones: 1 Sillón — N Turnos; N Bloqueos.

### Tratamiento
- Atributos: id, nombre ("Limpieza"), duracion_min (INT > 0), precio_referencia (nullable), activo.
- Relaciones: 1 Tratamiento — N Turnos.

### Turno
- Atributos: id, paciente_id, sillon_id, tratamiento_id, inicio (timestamptz), fin (calculado), estado (reservado|confirmado|asistido|cancelado|ausente), origen (online|mostrador), creado_en.
- Relaciones: N Turno — N RecordatorioWA; 0..1 Cobro de seña.
- Constraints: fin > inicio; CHECK anti-solapamiento por sillon (exclusión en rango); transición `cancelado` bloqueada si falta < 2 h (RN-TU-02).
- Índices: (sillon_id, inicio), (paciente_id, inicio), (estado, inicio).

### Bloqueo
- Atributos: id, sillon_id (nullable = todos), desde, hasta, motivo.

### RecordatorioWA
- Atributos: id, turno_id, tipo (recordatorio|confirmacion), plantilla, message_id proveedor, estado (enviado|entregado|leido|respondido|fallido), respuesta (confirmo|cancelo|null), creado_en.

### Cobro
- Atributos: id, turno_id, monto (centavos ARS), medio (efectivo|transferencia|mercadopago), tipo (seña|total), estado_mp (nullable: pendiente|aprobado), referencia_mp (nullable), creado_en.

## Seed data inicial

- 1 consultorio ("Consultorio demo"), 2 sillones activos.
- 3 tratamientos: Limpieza (30 min), Control (15 min), Conducto (60 min) — duraciones de ejemplo, editables.
- 3 usuarios: 1 secretaria, 1 odontólogo, 1 paciente de prueba (datos ficticios — nunca datos reales, ver README).
