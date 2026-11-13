# agenda/catalogo-config Specification

## Purpose

Permitir a la secretaria administrar sillones, tratamientos y bloqueos del consultorio con validación, historial preservado y trazabilidad de cada cambio, como base del cálculo futuro de disponibilidad.

## Requirements

### Requirement: Configuración exclusiva para secretaria

El sistema SHALL restringir todas las operaciones de `/api/config/sillones`, `/api/config/tratamientos` y `/api/config/bloqueos`, incluidas sus rutas por id, a usuarios activos autenticados con rol secretaria. SHALL responder 401 sin autenticación válida y 403 para paciente u odontólogo.

#### Scenario: Secretaria administra el catálogo

- **WHEN** una secretaria autenticada realiza una operación válida de catálogo
- **THEN** la API la procesa según el contrato del recurso

#### Scenario: Restricción por rol en cada operación

- **WHEN** un paciente u odontólogo intenta listar, consultar, crear, modificar o eliminar cualquiera de los tres recursos
- **THEN** recibe 403 sin leer datos de catálogo ni persistir cambios

#### Scenario: Anónimo no accede a configuración

- **WHEN** un cliente sin autenticación realiza cualquier operación de configuración
- **THEN** recibe 401 sin efectos persistentes

### Requirement: CRUD uniforme de catálogo

Cada recurso SHALL exponer POST de colección (201), GET de colección y por id (200), PATCH por id (200) y DELETE lógico por id (204). Un id inexistente SHALL responder 404. PATCH SHALL conservar campos omitidos, rechazar campos desconocidos y permitir null solo en atributos nullable.

#### Scenario: Ciclo de alta consulta y modificación

- **WHEN** una secretaria crea un recurso, consulta su id y modifica un atributo
- **THEN** recibe 201, 200 y 200 respectivamente, con el mismo id y los valores persistidos

#### Scenario: Recurso inexistente

- **WHEN** una secretaria consulta, modifica o elimina un UUID que no existe
- **THEN** recibe 404

#### Scenario: Modificación parcial conserva datos y valida null

- **WHEN** se envía PATCH omitiendo campos, enviando un campo desconocido o null en un atributo requerido
- **THEN** los omitidos se conservan y las entradas desconocidas o null no admitidos reciben 422 sin cambios

### Requirement: Listados paginados y filtrados

Los listados SHALL responder `{items,total,page,page_size}` con page desde 1, page_size entre 1 y 100, defaults 1/20, orden estable y filtro activo por defecto true. `activo=false` SHALL permitir consultar inactivos. Total SHALL contar solo registros coincidentes con el filtro.

#### Scenario: Página estable y total correcto

- **GIVEN** más registros activos que el tamaño de página solicitado
- **WHEN** se consultan páginas consecutivas sin cambios concurrentes
- **THEN** no se repiten registros y total coincide con la cantidad filtrada

#### Scenario: Filtro de inactivos y límites de página

- **WHEN** se consulta activo=false o se envía page=0 o page_size=101
- **THEN** el filtro devuelve inactivos y los parámetros fuera de rango reciben 422

### Requirement: Sillones con consultorio válido

El sistema SHALL crear y modificar sillones con nombre no vacío de hasta 80 caracteres y consultorio_id UUID. Al asignar consultorio, este SHALL existir y estar activo; referencia inexistente SHALL recibir 404 e inactiva 422. No SHALL aceptar metadatos de auditoría suministrados por el cliente.

#### Scenario: Alta de sillón válido

- **WHEN** una secretaria crea un sillón con nombre válido y consultorio activo existente
- **THEN** recibe 201 con el sillón vinculado y activo

#### Scenario: Validación de nombre y referencia

- **WHEN** se intenta asignar nombre vacío, demasiado largo, consultorio inexistente o inactivo
- **THEN** se rechaza con 422 para atributos inválidos/inactivos o 404 para referencia inexistente

### Requirement: Tratamientos con duración y precio en centavos

El sistema SHALL administrar tratamientos con nombre no vacío de hasta 120 caracteres, duracion_min entero estricto positivo y precio_referencia_centavos entero estricto no negativo o null. Ambos números SHALL caber en INTEGER PostgreSQL. SHALL rechazar floats y booleanos como duración o dinero con 422.

#### Scenario: Precio opcional y modificación de duración

- **WHEN** una secretaria crea un tratamiento de duración positiva sin precio y luego asigna un precio entero en centavos
- **THEN** ambas operaciones se persisten con el precio nullable y luego con el entero exacto

#### Scenario: Valores numéricos inválidos

- **WHEN** se envía duración cero/negativa, precio negativo, float, booleano o entero fuera de rango
- **THEN** la API responde 422 sin persistir cambios

#### Scenario: Limpiar precio explícitamente

- **WHEN** se envía PATCH con precio_referencia_centavos=null en un tratamiento existente
- **THEN** se elimina el precio de referencia conservando los demás atributos

### Requirement: Baja lógica conserva históricos

DELETE y desactivación por PATCH SHALL conservar las filas y sus relaciones, marcar is_active=false y deleted_at con zona horaria. Reactivar SHALL limpiar deleted_at. DELETE repetido sobre un recurso inactivo existente SHALL devolver 204 sin duplicar auditoría. Cambiar duración de un tratamiento SHALL NOT modificar inicio/fin de turnos existentes.

#### Scenario: Desactivar sillón conserva turnos

- **GIVEN** un sillón con turnos históricos
- **WHEN** una secretaria lo elimina mediante DELETE
- **THEN** se desactiva, conserva su fila y los turnos permanecen vinculados sin modificaciones

#### Scenario: Reactivación y baja repetida

- **WHEN** se desactiva dos veces un recurso y luego se reactiva
- **THEN** ambas bajas responden 204, solo la primera registra cambio y reactivar limpia deleted_at

#### Scenario: Cambio de duración conserva fin histórico

- **GIVEN** un tratamiento usado por un turno existente
- **WHEN** se modifica su duración
- **THEN** el turno conserva inicio y fin almacenados

### Requirement: Bloqueos generales y por sillón con rango válido

El sistema SHALL administrar bloqueos con sillon_id nullable (todos), desde/hasta con zona horaria, hasta mayor que desde y motivo no vacío de hasta 120 caracteres. Al asignar sillón específico SHALL existir y estar activo. PATCH SHALL validar el rango combinado con los valores almacenados, no solo los campos enviados.

#### Scenario: Bloqueo general y específico

- **WHEN** una secretaria crea un bloqueo con sillon_id=null y otro con un sillón activo existente
- **THEN** ambos se guardan y sus respuestas conservan el alcance solicitado

#### Scenario: Rechazo de fechas naive y rango inválido

- **WHEN** se crea o modifica un bloqueo con fechas sin zona horaria o hasta menor o igual a desde
- **THEN** la API responde 422 y conserva el estado anterior

#### Scenario: Validación de rango en actualización parcial

- **GIVEN** un bloqueo entre las 10:00 y 11:00 con zona horaria
- **WHEN** se modifica solo desde a las 12:00
- **THEN** se responde 422 por rango resultante inválido

### Requirement: Bloqueos solapados advierten y se permiten

Crear o modificar un bloqueo activo SHALL permitir persistirlo aunque se solape con turnos activos no cancelados ni ausentes. La respuesta SHALL incluir `warnings` con código TURNOS_SOLAPADOS y cantidad, o lista vacía. El rango SHALL ser semiabierto; el alcance general considera todos los sillones y el específico solo el asignado. No SHALL modificar turnos.

#### Scenario: Bloqueo solapado con turno existente

- **GIVEN** un turno activo en el sillón afectado
- **WHEN** se crea o modifica un bloqueo activo que ocupa parte de ese turno
- **THEN** se guarda el bloqueo, se informa TURNOS_SOLAPADOS con la cantidad correcta y el turno se conserva

#### Scenario: Bloqueo general considera todos los sillones

- **WHEN** se crea un bloqueo general que coincide con turnos activos en dos sillones
- **THEN** la cantidad advertida incluye los turnos de ambos sillones

#### Scenario: Adyacencia y turnos no bloqueantes no generan aviso

- **WHEN** un bloqueo solo toca el extremo de un turno, coincide con cancelados/ausentes/inactivos o se refiere a otro sillón
- **THEN** esos turnos no suman advertencias

### Requirement: Auditoría de configuración transaccional

Cada cambio efectivo SHALL guardar recurso, id, acción, autor autenticado, fecha con zona horaria y snapshots de catálogo antes/después en la misma transacción. El cliente SHALL NOT decidir autor o fecha. Si falla la auditoría SHALL revertirse la mutación. Los eventos SHALL NOT incluir credenciales ni datos de pacientes.

#### Scenario: Alta modificación baja y reactivación auditadas

- **WHEN** una secretaria crea, modifica, desactiva o reactiva un recurso
- **THEN** se persiste un evento con su usuario, acción, tiempo y snapshots correspondientes al cambio

#### Scenario: Falla de auditoría revierte catálogo

- **WHEN** falla la persistencia del evento durante una mutación
- **THEN** no queda persistido ni el cambio de catálogo ni un evento parcial

### Requirement: Contexto administrativo de consultorio único
La API SHALL exponer a secretaria autenticada el identificador y nombre del único consultorio activo de una instalación de sede única. Si hay cero o más de uno SHALL indicar contexto no disponible sin elegir uno. Pacientes y odontólogos SHALL recibir 403 y anónimos 401.

#### Scenario: Único consultorio activo
- **WHEN** una secretaria solicita el contexto y existe exactamente un consultorio activo
- **THEN** recibe su identificador y nombre para crear sillones, incluso si todavía no existen sillones

#### Scenario: Contexto ausente o ambiguo
- **WHEN** no existen consultorios activos o existen dos o más
- **THEN** no se devuelve ningún identificador utilizable ni se crea o modifica un consultorio

#### Scenario: Acceso no autorizado
- **WHEN** un anónimo, paciente u odontólogo solicita contexto administrativo
- **THEN** recibe 401 o 403 según corresponda sin datos del consultorio
