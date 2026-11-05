# Flujos Principales

Cada flujo se documenta extremo a extremo. Actores y permisos en `03_actores_y_roles.md`.

## Flujo 1: Reserva online del paciente
**Disparador**: el paciente entra a `/horarios`. **Actor**: paciente (anónimo → logueado).

**Pasos**:
1. PWA pide `GET /horarios-libres` (fecha, sillón, tratamiento).
2. API calcula disponibilidad (sillones activos − turnos − bloqueos, duración del tratamiento).
3. Paciente elige horario → login/registro (RN-AU-01).
4. Si hay seña: checkout Mercado Pago → webhook aprueba → se crea el turno; si no: se crea directo.
5. API verifica anti-solapamiento a nivel motor antes de confirmar (RN-TU-01).
6. Sistema agenda el recordatorio WhatsApp (RN-NT-01).

**Casos de error**:
- Hueco ocupado en el medio → 409 + oferta de alternativas (RN-TU-01).
- Pago rechazado → turno no creado, mensaje claro (RN-CO-01).
- Falla WhatsApp → el turno existe igual; reintento encolado (RN-NT-03).

## Flujo 2: Confirmación / cancelación por WhatsApp
**Disparador**: respuesta del paciente al mensaje con botón. **Actor**: paciente vía proveedor.

**Pasos**:
1. Webhook recibe `confirmo|cancelo` + message_id.
2. API matchea el turno, valida ventana de 2 h si es cancelación (RN-TU-02).
3. Actualiza estado y registra la respuesta (RN-NT-02/03).

**Casos de error**:
- Cancelación < 2 h → se rechaza con explicación y se ofrece llamar al consultorio.
- Mensaje duplicado → idempotencia por message_id.

## Flujo 3: Agenda del día (odontólogo)
**Disparador**: inicio de jornada. **Actor**: odontólogo.

**Pasos**:
1. PWA pide `GET /agenda?fecha=hoy`.
2. API devuelve turnos por sillón con estados y tolerancia visible (RN-TU-05).
3. Odontólogo atiende; secretaria marca asistencia/ausencia.

**Casos de error**:
- Turno sin confirmar a la hora → se marca ausente, libera para lista de espera futura.

## Flujo 4: Cobro y asignación en local (secretaria)
**Disparador**: paciente en mostrador. **Actor**: secretaria.

**Pasos**:
1. Secretaria abre el turno y registra cobro (`POST /cobros`: medio + monto).
2. Sistema concilia seña previa si existía (RN-CO-02).
3. Turno queda asignado/cobrado; sin factura electrónica (RN-CO-03 explícito).

**Casos de error**:
- Monto inconsistente con tratamiento → advertencia, permite override auditado.
