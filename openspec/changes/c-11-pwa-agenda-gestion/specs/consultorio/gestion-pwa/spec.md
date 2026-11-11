# Spec Delta

## Purpose

Permitir al equipo del consultorio consultar y gestionar su agenda, configuración
y cobros desde una PWA accesible, sin sustituir las reglas del backend ni exponer
datos privados entre roles o cuentas.

## ADDED Requirements

### Requirement: Navegación del consultorio por rol
La PWA SHALL permitir /agenda a secretaria y odontólogo, y /config y registro en /cobros solo a secretaria. SHALL esperar verificación de sesión antes de solicitar datos privados. Paciente SHALL recibir acceso denegado sin solicitudes administrativas; anónimo SHALL ir a login con retorno interno validado. Backend SHALL seguir autorizando cada solicitud.

#### Scenario: Secretaria ingresa a configuración
- **WHEN** una secretaria ingresa mediante un enlace directo a /config
- **THEN** se restaura su sesión y se muestra configuración solo tras verificar su rol

#### Scenario: Paciente y anónimo
- **WHEN** un paciente o un anónimo intenta abrir /agenda o /cobros
- **THEN** se deniega al paciente sin cargar datos y al anónimo se le ofrece login sin redirección externa

### Requirement: Agenda diaria por sillón con fecha argentina
La PWA SHALL mostrar la agenda del día seleccionado en America/Argentina/Buenos_Aires, agrupada por sillón y ordenada por inicio, con filtros de sillón y estado. Cada turno SHALL mostrar paciente, tratamiento, inicio/fin, estado y tolerancia del servidor. SHALL diferenciar carga, vacío y error e ignorar respuestas de filtros anteriores.

#### Scenario: Día y filtros
- **WHEN** el personal elige fecha, sillón y estado
- **THEN** ve solo los turnos correspondientes al día argentino y filtros vigentes, con fechas y horas explícitas

#### Scenario: Medianoche argentina y respuesta tardía
- **WHEN** hay turnos alrededor de medianoche o una respuesta anterior llega después de cambiar fecha
- **THEN** no se omiten turnos del día elegido ni se incluyen de otro día, y la respuesta anterior no reemplaza la vista actual

### Requirement: Sobreturnos y conflictos visibles
La PWA SHALL identificar sobreturnos mediante texto y motivo del servidor. Ante 409 de gestión SHALL explicar el conflicto y presentar alternativas para elección explícita, sin guardar automáticamente ni ofrecer eludir EXCLUDE. SHALL NOT convertir una alerta en autorización de solapamiento.

#### Scenario: Sobreturno existente
- **WHEN** la agenda incluye es_sobreturno y motivo
- **THEN** se muestra una marca textual distinguible y el motivo, sin depender solo del color

#### Scenario: Reprogramación en conflicto
- **WHEN** el servidor rechaza una reprogramación con 409
- **THEN** se conserva el turno original, se explica el conflicto y se ofrecen las alternativas recibidas sin seleccionar ninguna automáticamente

### Requirement: Gestión explícita con reglas del servidor
La PWA SHALL ofrecer confirmar, cancelar y reprogramar a secretaria según permisos/transiciones vigentes, y marcar asistencia a secretaria/odontólogo según contrato backend. Cancelar/reprogramar SHALL respetar la ventana mínima del servidor también para secretaria. Una negativa 422 SHALL explicar su causa sin fingir éxito ni inventar una ventana adicional para confirmar o asistencia.

#### Scenario: Cambio confirmado
- **WHEN** una secretaria confirma una acción permitida y el servidor devuelve el turno actualizado
- **THEN** se muestra el estado persistido y se refresca la agenda sin repetir la escritura

#### Scenario: Ventana y transición vencidas
- **WHEN** faltan menos de 2 horas o cambió el estado desde la lectura y el servidor rechaza cancelar/reprogramar
- **THEN** se muestra la restricción y se consulta nuevamente el estado sin permitir una excepción por rol secretaria

### Requirement: Historial auténtico de gestión
La PWA SHALL mostrar quién, cuándo y origen de los cambios únicamente desde registros auditados autorizados del backend. SHALL NOT presentar updated_at o el origen actual como historial completo. Si la fuente no está disponible SHALL indicarlo sin inventar eventos; la ausencia de evidencia SHALL impedir dar por aceptado el historial.

#### Scenario: Historial disponible
- **WHEN** secretaria u odontólogo autorizado abre el historial de un turno
- **THEN** ve los eventos persistidos con actor, fecha con zona y origen, no valores suministrados por el cliente

#### Scenario: Fuente ausente
- **WHEN** el historial no puede consultarse
- **THEN** se muestra indisponibilidad y no se inventa autor, secuencia de cambios ni afirmación de auditoría completa

### Requirement: Configuración paginada y baja lógica
La PWA SHALL permitir a secretaria listar, crear, editar, desactivar y reactivar sillones, tratamientos y bloqueos mediante contratos administrativos, con paginación y filtro activo/inactivo. SHALL conservar campos omitidos en PATCH, permitir null solo donde corresponde y explicar que desactivar no borra históricos. SHALL obtener identificadores desde contexto autorizado, no pedir UUID manuales.

#### Scenario: Editar y reactivar
- **WHEN** secretaria modifica un nombre o reactiva un recurso inactivo
- **THEN** se envían solo los cambios necesarios, se conserva el resto y se refleja la respuesta del servidor

#### Scenario: Contexto de consultorio faltante
- **WHEN** se intenta crear el primer sillón sin contexto de consultorio autorizado disponible
- **THEN** se informa que falta configuración inicial y no se inventa un consultorio ni se exige escribir un UUID

### Requirement: Validación clara de tratamientos y bloqueos
La PWA SHALL editar duración entera positiva, precio nullable en centavos y bloqueos generales o por sillón con fechas aware. SHALL mostrar errores 422 y warnings TURNOS_SOLAPADOS sin confundir advertencia con rechazo ni cancelar turnos. Campos de política de seña SHALL permanecer no editables hasta verificar su contrato dependiente.

#### Scenario: Bloqueo con advertencia
- **WHEN** el servidor persiste un bloqueo y devuelve TURNOS_SOLAPADOS
- **THEN** se muestra guardado con la cantidad advertida y los turnos existentes se conservan

#### Scenario: Duración o rango inválido
- **WHEN** se recibe 422 por duración o por hasta menor o igual a desde
- **THEN** se asocia el error a los campos, se conservan sus valores y no se anuncia guardado

### Requirement: Cobro local incremental y verificado
La PWA SHALL registrar cobros solo para secretaria y un turno real seleccionado, en centavos ARS enteros con medio/tipo y clave idempotente por operación. SHALL mostrar seña previa, dinero nuevo, totales y saldo según contrato verificado. SHALL indicar sin factura electrónica en v1. Si el contrato monetario no está verificado SHALL bloquear el envío, no simular un cobro.

#### Scenario: Conciliación incremental
- **GIVEN** precio ficticio 10000 centavos y seña verificada de 3000
- **WHEN** secretaria registra 7000 centavos nuevos y el servidor confirma
- **THEN** se muestran 10000 cobrados y saldo cero, sin registrar otra vez la seña

#### Scenario: Contrato dependiente bloqueado
- **WHEN** falta verificación de totales, unicidad de cierre o recuperación de resultado ambiguo
- **THEN** registrar cobro permanece deshabilitado con explicación y no se envían escrituras monetarias

### Requirement: Diferencias y replays monetarios explícitos
Ante MONTO_DIFIERE la PWA SHALL mostrar esperado/recibido y pedir motivo de override y nueva confirmación antes de enviar el payload modificado con nueva clave. SHALL preservar la clave para la misma operación. Replays SHALL mostrar el mismo cobro sin sumar otra vez. SHALL NOT calcular un cierre autoritativo ocultando discrepancias del servidor.

#### Scenario: Override consentido
- **WHEN** servidor devuelve MONTO_DIFIERE y secretaria decide continuar con motivo
- **THEN** se envía una nueva operación explícita con motivo y nueva clave, mostrando la advertencia auditada al confirmar

#### Scenario: Replay o segundo cierre
- **WHEN** el servidor devuelve un replay o rechaza un cierre ya registrado
- **THEN** se conserva el cobro original y no se incrementa el total localmente ni se ofrece reintento automático

### Requirement: Recuperación de escrituras inciertas
Una escritura con resultado desconocido SHALL bloquear su repetición ciega y ofrecer consulta de estado verificable. La PWA SHALL NOT reenviar POST/PATCH/DELETE al reconectar ni tras refresh de autenticación. Una lectura vacía o fallida SHALL NOT demostrar que el cobro o cambio no se aplicó.

#### Scenario: Respuesta de cobro perdida
- **WHEN** se pierde conexión después de enviar un cobro
- **THEN** se informa resultado no verificado y se conserva la identidad de la operación para reconciliar sin crear otra

#### Scenario: Reconexión
- **WHEN** vuelve la red tras una acción de gestión incierta
- **THEN** solo se hacen lecturas de recuperación, sin repetir la escritura pendiente ni mostrar éxito sin evidencia

### Requirement: Privacidad y accesibilidad operativas
La PWA SHALL mantener datos clínicos/agenda/cobros solo en memoria y purgarlos en logout/cambio de cuenta. SHALL NOT persistirlos en cachés, storage ni colas offline. SHALL distinguir navegación HTML de API JSON homónimas y funcionar con teclado a 360px, 390px y escritorio, con foco, labels, mensajes accesibles y controles táctiles.

#### Scenario: Cambio de cuenta
- **WHEN** sale una secretaria e ingresa otra cuenta o paciente, incluso con respuestas pendientes
- **THEN** no quedan turnos, cobros ni formularios privados de la cuenta anterior visibles o persistidos

#### Scenario: Offline y navegación accesible
- **WHEN** el personal usa teclado o abre /agenda offline
- **THEN** puede reconocer controles y restricciones; offline solo ofrece shell público sin datos privados cacheados ni acciones habilitadas
