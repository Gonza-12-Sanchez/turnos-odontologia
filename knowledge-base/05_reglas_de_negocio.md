# Reglas de Negocio

Cada regla tiene código único `RN-{DOMINIO}-{NN}` para trazabilidad (usado en `06_funcionalidades.md`).

## Dominio: Turnos (RN-TU)

- **RN-TU-01**: Prohibida la doble reserva — no pueden existir dos turnos activos solapados en el mismo sillón/horario. Se garantiza a nivel de motor (constraint de exclusión), no solo de UI.
- **RN-TU-02**: Cancelación mínima 2 h antes — el sistema bloquea cancelar/reprogramar cuando faltan menos de 2 h para el inicio. Vale para paciente y secretaria.
- **RN-TU-03**: La duración del turno la determina el tratamiento (fin = inicio + duración). No existe "turno estándar fijo".
- **RN-TU-04**: Multi-sillón desde el día 1 — todo turno pertenece a un sillón; la disponibilidad se calcula por sillón.
- **RN-TU-05**: Tolerancia de llegada tarde de 5 min, visible en agenda (informativa, no bloquea).
- **RN-TU-06**: Bloqueos (feriados, almuerzo, mantenimiento) quitan disponibilidad; un sobreturno solo lo crea la secretaria y puede solaparse de forma explícita y marcada.

## Dominio: Autenticación (RN-AU)

- **RN-AU-01**: Reservar exige paciente con login (nombre + teléfono no alcanza). Ver horarios libres es público; reservar no.
- **RN-AU-02**: Sesiones por rol (paciente | odontólogo | secretaria); la matriz RBAC vive en `03_actores_y_roles.md`. Esquema de credential (password vs OTP-WhatsApp) a decidir — ver IN-10-03.

## Dominio: Notificaciones (RN-NT)

- **RN-NT-01**: Todo turno reservado genera recordatorio automático por WhatsApp (plantilla Meta) con botón confirmar/cancelar.
- **RN-NT-02**: La respuesta del paciente (confirmo/cancelo) actualiza el estado del turno; cancelar por WhatsApp respeta RN-TU-02.
- **RN-NT-03**: Cada envío y respuesta queda registrado (RecordatorioWA) con estado de entrega.

## Dominio: Cobros (RN-CO)

- **RN-CO-01**: Seña por Mercado Pago opcional al reservar ("el que paga viene"); si se exige seña para un tratamiento, sin pago no hay reserva.
- **RN-CO-02**: El cobro en local (efectivo/transferencia/MP) se registra contra el turno y la secretaria puede asignar turnos cobrados.
- **RN-CO-03**: Montos siempre en centavos ARS; sin facturación electrónica en v1 (ARCA = fase 2).

## Dominio: Excepciones globales

- **RN-GL-01**: Ninguna regla de UI sustituye a su constraint de motor (RN-TU-01/02 se verifican en backend aunque el cliente no las pida).
- **RN-GL-02**: Nunca se almacenan datos reales de pacientes en repo, seeds ni ejemplos.
- **RN-GL-03**: Todo cambio de estado de turno es auditable (quién, cuándo, origen online/mostrador/WhatsApp).
