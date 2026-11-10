# cobros/registro Specification

## Purpose
Registrar cobros contra turnos, conciliar senas ya recibidas y mantener trazabilidad monetaria y acceso autorizado sin facturacion electronica.

## Requirements

### Requirement: Cobro local autorizado y exacto
El sistema SHALL exponer POST /cobros solo para secretaria, con turno_id, monto_centavos entero estricto positivo, medio efectivo|transferencia|mercadopago y tipo sena|total. SHALL rechazar importes fuera de INTEGER, floats y booleanos con 422. El monto SHALL representar dinero nuevo recibido, nunca el total bruto incluyendo senas previas.

#### Scenario: Cobro valido en mostrador
- **WHEN** una secretaria registra 7000 centavos nuevos contra un turno existente con medio efectivo y tipo total
- **THEN** recibe 201 y un cobro por exactamente 7000 centavos vinculado al turno

#### Scenario: Autorizacion y validacion de dinero
- **WHEN** un anonimo, un paciente o una secretaria con monto 12.5 intenta registrar un cobro
- **THEN** recibe respectivamente 401, 403 o 422 sin movimiento monetario

### Requirement: Conciliacion sin duplicar sena
El sistema SHALL sumar solo movimientos efectivos una vez y devolver sena_acumulada_centavos, total_cobrado_centavos y saldo_referencia_centavos. Un cierre total SHALL descontar las senas existentes; no modificara la maquina de estados de Turno. Precio sin referencia SHALL producir saldo null y warning PRECIO_SIN_REFERENCIA.

#### Scenario: Saldo despues de sena aprobada
- **WHEN** un turno de precio 10000 tiene sena aprobada de 3000 y se registra cierre por 7000
- **THEN** total_cobrado es 10000, saldo es 0 y la sena no se registra otra vez

#### Scenario: Precio desconocido
- **WHEN** se registra cobro para un tratamiento con precio_referencia_centavos null
- **THEN** se preserva el monto exacto, saldo es null y se devuelve PRECIO_SIN_REFERENCIA

### Requirement: Diferencia de precio requiere override auditado
Para un cierre que difiere del precio de referencia, el sistema SHALL responder 409 con code MONTO_DIFIERE y valores esperado/recibido sin registrar cobro. Una secretaria SHALL poder repetir con override_motivo no vacio para registrar y recibir advertencia. Autor, instante aware y motivo SHALL quedar auditados atomicamente con el cobro.

#### Scenario: Diferencia detectada sin efecto
- **WHEN** se intenta cerrar por 6000 un saldo esperado de 7000 sin motivo
- **THEN** se responde 409 MONTO_DIFIERE y no se agrega un cobro

#### Scenario: Override explicito
- **WHEN** la secretaria confirma esos 6000 con motivo valido
- **THEN** se registra el cobro, la diferencia y la identidad del autor en la misma operacion auditada

### Requirement: Idempotencia y cierre concurrente
POST /cobros SHALL requerir Idempotency-Key y devolver el mismo cobro ante replay del mismo actor y payload, con 200 sin repetir efectos. Reusar clave con payload distinto SHALL responder 409. Cierres concurrentes con distintas claves o una segunda sena del mismo turno SHALL NOT duplicar el cierre o la sena.

#### Scenario: Replay de cobro
- **WHEN** se repite el mismo cobro con igual clave
- **THEN** se devuelve el id original y los totales no se incrementan nuevamente

#### Scenario: Dos cierres concurrentes
- **WHEN** se envian dos cierres del mismo turno con claves distintas simultaneamente
- **THEN** solo uno se registra y el otro recibe 409 sin duplicar el ingreso

### Requirement: Lectura de cobros respeta propiedad y rol
GET /cobros?turno_id= SHALL permitir lectura a secretaria y odontologo y solo lectura propia al paciente. Recursos ajenos para paciente SHALL devolver 404, anonimo 401. La proyeccion paciente SHALL excluir referencias privadas del proveedor y datos de otros pacientes.

#### Scenario: Paciente consulta cobros propios
- **WHEN** un paciente consulta el turno que le pertenece
- **THEN** recibe sus movimientos y totales sin datos privados MP

#### Scenario: Paciente intenta otro turno
- **WHEN** un paciente consulta el turno de otro paciente
- **THEN** recibe 404 sin confirmar existencia ni exponer cobros ajenos

### Requirement: Registro local no equivale a pago MP verificado ni factura
Un cobro mercadopago declarado manualmente SHALL mantener estado_mp null y no fingir verificacion online. Las respuestas de registro SHALL indicar facturacion_electronica false; no se emitira factura ni se alterara un pago del proveedor.

#### Scenario: Mercado Pago manual
- **WHEN** una secretaria declara un cobro local con medio mercadopago
- **THEN** se registra como movimiento manual, sin referencia MP aprobada inventada y con facturacion_electronica false

#### Scenario: Auditoria falla
- **WHEN** no puede persistirse auditoria del cobro o override
- **THEN** no se confirma ni el movimiento ni sus efectos parciales
