# Spec Delta

> Spec canónico: `openspec/specs/cobros/sena-mp/spec.md`. Este archivo es un delta del change archivado C-09; la fuente de verdad vigente está en la ruta indicada.

## Purpose

Gestionar senas Mercado Pago desde una politica servidor hasta la verificacion del pago y su aplicacion unica a una reserva, sin confundir dinero recibido con cupo confirmado.

## ADDED Requirements

### Requirement: Politica de sena por tratamiento
El sistema SHALL administrar sena_politica deshabilitada|opcional|obligatoria y sena_centavos en los endpoints administrativos existentes de tratamientos, solo secretaria. En opcional/obligatoria SHALL exigir entero estricto positivo dentro de INTEGER; deshabilitada SHALL tener monto null por defecto. La politica SHALL decidirse en servidor y auditarse.

#### Scenario: Tratamiento exige sena sin flag cliente
- **WHEN** un paciente intenta reservar un tratamiento obligatorio omitiendo flags o enviandolos false
- **THEN** el servidor exige sena y no permite reservar sin pago

#### Scenario: Politica incoherente rechazada
- **WHEN** la secretaria activa sena obligatoria sin monto o envia float, booleano o monto negativo
- **THEN** recibe 422 sin alterar tratamiento ni auditoria parcialmente

### Requirement: Intento propio con checkout sin crear turno
POST /pagos/sena SHALL aceptar paciente autenticado, sillon_id, tratamiento_id e inicio aware e Idempotency-Key. SHALL validar hueco y politica, persistir intento y devolver checkout con provider, status, intento_id, checkout_url, expires_at, monto_centavos, moneda ARS y modo. No SHALL crear ni retener un turno antes de pago. Intentos nuevos SHALL recibir 201 y replays 200.

#### Scenario: Checkout valido
- **WHEN** un paciente solicita sena para un hueco libre de tratamiento habilitado
- **THEN** recibe checkout con importe servidor, vencimiento e intento propio, sin turno creado

#### Scenario: Hueco ocupado antes de pagar
- **WHEN** se solicita checkout de un hueco ocupado
- **THEN** recibe 409 con alternativas y no se le ofrece pagar ese hueco

### Requirement: Creacion de checkout idempotente y resultados ambiguos
La misma clave, actor y payload SHALL recuperar el intento sin generar otro cobro ni checkout. Clave con payload distinto SHALL devolver 409. Un timeout de creacion cuyo resultado remoto sea desconocido SHALL conservar el intento como creando_checkout o requiere_revision y SHALL NOT recrear automaticamente una preferencia.

#### Scenario: Repeticion de solicitud
- **WHEN** se repite la misma solicitud con la misma clave tras perder la respuesta
- **THEN** se recupera el intento original y no se genera otra preferencia a ciegas

#### Scenario: Clave usada para otro horario
- **WHEN** se cambia inicio manteniendo una clave ya utilizada
- **THEN** se responde 409 sin alterar el intento previo

### Requirement: Webhook autenticado y pago consultado en proveedor
POST /webhooks/mercadopago SHALL validar firma y formato del evento payment y consultar el pago por id en MP. SHALL verificar referencia, importe exacto, moneda ARS, receptor y modo contra el intento. Redireccion del navegador o estado enviado por cliente SHALL NOT aprobar pagos. Firma invalida SHALL recibir 401, error transitorio 503 sin exito ficticio.

#### Scenario: Pago aprobado verificado
- **WHEN** llega notificacion valida y MP confirma approved con importe, referencia, receptor y modo correctos
- **THEN** el pago puede aplicarse a ese intento despues de revalidar el hueco

#### Scenario: Firma o datos financieros falsos
- **WHEN** llega firma invalida o MP informa importe/moneda/receptor que no coincide
- **THEN** no se crea turno ni cobro aplicado y se rechaza o registra incidencia sin exponer secretos

### Requirement: Aplicacion atomica e idempotente de pago
Un pago approved valido SHALL crear a lo sumo un turno reservado, una sena Cobro aprobada y su auditoria, con actualizacion atomica del intento. La referencia de pago SHALL ser unica. Webhooks duplicados, concurrentes o fuera de orden SHALL NOT duplicar efectos ni degradar una reserva aplicada. Fallo transitorio antes de persistencia durable SHALL permitir reintento.

#### Scenario: Notificacion duplicada concurrente
- **WHEN** llegan dos notificaciones simultaneas del mismo payment_id aprobado
- **THEN** existe un solo turno y una sola sena aplicada y el replay se reconoce sin duplicacion

#### Scenario: Evento pendiente atrasado
- **WHEN** llega un evento antiguo despues de aplicar approved y la consulta MP sigue approved
- **THEN** la reserva y la sena siguen aplicadas una sola vez

### Requirement: Pago recibido sin cupo requiere revision
Un pago approved sin hueco valido, posterior al vencimiento, de duracion cambiada o segundo pago del mismo intento SHALL conservarse como incidencia durable requiere_revision sin turno adicional ni sobreturno. SHALL respetarse EXCLUDE. Pago rejected SHALL dejar el intento sin reserva. Fecha de aprobacion proveedor SHALL decidir vencimiento, no fecha de recepcion del webhook.

#### Scenario: Carrera entre checkout y otra reserva
- **WHEN** se aprueba un pago pero otro paciente ocupo el hueco
- **THEN** se registra el pago y la incidencia, sin turno ni cobro aplicado a otro turno y se indica contactar al consultorio

#### Scenario: Pago rechazado
- **WHEN** MP verifica que el pago fue rechazado
- **THEN** se informa rechazado y no se crea turno ni sena aprobada

#### Scenario: Redelivery posterior al vencimiento
- **WHEN** un pago fue aprobado antes de expires_at pero el webhook llega despues y el hueco sigue valido y futuro
- **THEN** se puede aplicar sin penalizar la demora de entrega

### Requirement: Consulta de estado propia y resolucion auditada
GET /pagos/sena/{id} SHALL exponer estado, monto, moneda, expiracion, turno_id y requiere_contacto solo al propietario (ajeno/inexistente 404). Secretaria SHALL poder listar incidencias paginadas y registrar resolucion manual con motivo y referencia. Registrar resolucion SHALL NOT ejecutar refund ni fingir reserva. Pagos recibidos SHALL NOT borrarse por expirar el checkout.

#### Scenario: Retorno pendiente no confirma
- **WHEN** el propietario consulta un intento pendiente despues de volver de MP
- **THEN** recibe pendiente y turno_id null, aunque el navegador haya enviado status approved

#### Scenario: Resolucion por secretaria
- **WHEN** la secretaria registra una devolucion hecha en panel MP con motivo y referencia
- **THEN** queda auditada la resolucion operacional sin afirmar que el sistema ejecuto una devolucion automatica

### Requirement: Recuperacion sin perder dinero ni recordatorios
El sistema SHALL poder reconciliar intentos pendientes cuando falte webhook usando verificacion servidor e idempotencia equivalentes. Tras reserva aplicada SHALL invalidar disponibilidad y generar recordatorio por el circuito existente; falla de notificaciones SHALL NOT revertir pago o turno y SHALL permitir recuperacion durable.

#### Scenario: Webhook no entregado
- **WHEN** la reconciliacion encuentra un pago approved verificable para un intento pendiente
- **THEN** aplica las mismas validaciones sin duplicar un pago ya aplicado

#### Scenario: Redis no disponible tras commit
- **WHEN** se confirma turno y cobro pero no puede encolarse recordatorio
- **THEN** turno y cobro permanecen y el recordatorio queda recuperable sin duplicar la reserva

### Requirement: Modos de pago y minimizacion de datos
Los modos disabled, mock, sandbox y production SHALL estar separados y fallar cerrado por configuracion incompleta. Mock SHALL NOT estar permitido en produccion ni aceptar aprobacion publica sin verificacion. Credenciales SHALL permanecer en backend/env. Checkout y registros SHALL minimizar datos: sin tarjetas, notas clinicas ni tratamiento en metadata del proveedor, ni payloads completos en logs.

#### Scenario: Sena obligatoria con integracion deshabilitada
- **WHEN** se intenta pagar con MP disabled o credenciales incompletas
- **THEN** se informa indisponibilidad sin crear reserva gratis ni activar mock implicitamente

#### Scenario: Checkout sandbox
- **WHEN** se prueba sandbox con datos ficticios
- **THEN** se identifica el modo, se usan credenciales de prueba externas al repo y ningun secreto llega a la PWA
