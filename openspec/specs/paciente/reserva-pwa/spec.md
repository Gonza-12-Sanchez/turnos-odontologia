# paciente/reserva-pwa Specification

## Purpose
Permitir al paciente consultar horarios, autenticarse, reservar y gestionar sus propias reservas desde una PWA movil accesible, preservando la autoridad del backend y la privacidad.

## Requirements

### Requirement: Navegacion publica y filtros reales
La PWA SHALL ofrecer /, /horarios, /login y /registro publicos, y /mis-reservas protegido para paciente. Horarios SHALL obtener catalogo y disponibilidad reales por fecha, tratamiento y sillon opcional sin login. SHALL distinguir carga, vacio, error y offline, presentar zona horaria AR y no mostrar pacientes ajenos ni rutas administrativas.

#### Scenario: Anonimo ve franjas por filtros
- **WHEN** un anonimo elige tratamiento, fecha y sillon
- **THEN** ve franjas devueltas por /horarios-libres sin credenciales y con fechas/horas locales claras

#### Scenario: Sin horarios o consulta fallida
- **WHEN** la API devuelve lista vacia o falla la consulta
- **THEN** la PWA diferencia falta de cupos de error de servicio y ofrece cambiar filtros o reintentar segun corresponda

### Requirement: Sesion respeta contratos de autenticacion existentes
La PWA SHALL registrar nombre/email/telefono/password y tratar 201 como cuenta creada, no sesion. SHALL iniciar sesion con login, restaurar por refresh y usar /auth/me para rol. Access token SHALL vivir solo en memoria y refresh solo en cookie HttpOnly. Logout SHALL limpiar datos privados locales e informar fallos de cierre servidor.

#### Scenario: Registro seguido de ingreso
- **WHEN** registro devuelve UserOut sin token
- **THEN** la PWA ofrece login explicito y no asume autenticacion ni guarda password

#### Scenario: Sesion expirada o rol incorrecto
- **WHEN** refresh devuelve 401 o el usuario autenticado no es paciente
- **THEN** se solicita ingreso o se explica restriccion de rol sin cargar reservas ni pantallas administrativas

### Requirement: Login preserva seleccion sin reenviar reservas
Al reservar anonimamente la PWA SHALL solicitar login conservando solo filtros/horario no sensibles y destino interno validado. Tras login SHALL revalidar disponibilidad y pedir confirmacion de reserva. No SHALL aceptar redireccion externa mediante returnTo ni reenviar POST automaticamente.

#### Scenario: Continuar despues de login
- **WHEN** un anonimo elige hora e inicia sesion
- **THEN** recupera seleccion y confirma explicitamente despues de nueva comprobacion

#### Scenario: Destino de retorno externo
- **WHEN** login recibe returnTo con URL externa o ruta no permitida
- **THEN** no redirige a ese destino y ofrece navegacion interna segura

### Requirement: Reserva interpreta errores estructurados
La PWA SHALL enviar POST /turnos autenticado sin precio/fin cliente. SHALL mostrar exito solo por 201, ofrecer alternativas de 409 para eleccion explicita y mostrar errores 422/401/403/503 accionables. Una respuesta tardia de filtros anteriores SHALL NOT reemplazar la seleccion vigente. Una escritura de resultado ambiguo SHALL NOT reenviarse ciegamente.

#### Scenario: Turno creado
- **WHEN** POST /turnos devuelve 201
- **THEN** se muestra reserva registrada con datos del servidor y se actualizan las reservas propias

#### Scenario: Hueco tomado con alternativas
- **WHEN** POST devuelve 409 con alternativas o lista vacia
- **THEN** se ofrecen opciones explicitamente elegibles o cambiar filtros sin afirmar que se reservo

#### Scenario: Respuesta perdida
- **WHEN** se corta la red despues de enviar una reserva
- **THEN** se informa resultado no verificado y se ofrece consultar Mis reservas antes de intentar nuevamente

### Requirement: Checkout y retorno no equivalen a reserva
Ante 402 la PWA SHALL consumir checkout C-09, mostrar importe/moneda/modo, advertir revalidacion de cupo y redirigir solo a destino permitido. /pagos/retorno SHALL consultar GET /pagos/sena/{id} autenticado. Solo estado aprobado con turno_id SHALL mostrar reserva efectiva; parametros MP en URL SHALL NOT decidir estado.

#### Scenario: Sena requerida
- **WHEN** se recibe 402 con checkout valido y modo sandbox o production
- **THEN** se muestra importe y advertencia de cupo antes de dirigir a checkout permitido sin exponer credenciales

#### Scenario: Retorno falso aprobado
- **WHEN** la URL indica approved pero el servidor informa pendiente
- **THEN** se muestra pendiente, se consulta de forma acotada y no se muestra turno confirmado

#### Scenario: Pago con incidencia o rechazo
- **WHEN** servidor informa requiere_revision, rechazado o expirado
- **THEN** no se muestra reserva; revision indica contactar consultorio sin volver a cobrar y rechazo/expiracion permite volver a horarios

### Requirement: Mis reservas y acciones servidor
La PWA SHALL listar solo respuesta propia de /mis-reservas, con fecha, tratamiento, sillon, estado y tolerancia_min. SHALL ofrecer confirmar/cancelar segun acciones del servidor mediante PATCH existentes. Cancelar SHALL pedir confirmacion; 422 por ventana vencida SHALL explicar limite minimo y refrescar datos. No SHALL inventar bloqueo adicional de confirmar ni ofrecer reprogramacion en C-10.

#### Scenario: Reserva con acciones permitidas
- **WHEN** el servidor permite confirmar o cancelar y el paciente elige una accion
- **THEN** se envia el PATCH correspondiente y se actualiza estado con respuesta servidor

#### Scenario: Ventana de cancelacion vencida
- **WHEN** acciones.cancelar es false o el PATCH devuelve 422 porque faltan menos de 2 horas
- **THEN** se explica la restriccion sin anunciar cancelacion exitosa ni sustituir validacion backend

### Requirement: PWA instalable sin datos privados offline
La PWA SHALL incluir manifest e iconos instalables y shell publico offline. SHALL NOT cachear respuestas API, tokens, passwords, reservas ni pagos en almacenamiento persistente. Offline SHALL deshabilitar escrituras y no ofrecer disponibilidad como actual; no SHALL encolar reservas/pagos para reenvio. Actualizaciones SHALL pedir permiso antes de recargar formularios.

#### Scenario: App instalada sin conexion
- **WHEN** una PWA instalada se abre offline
- **THEN** muestra shell y aviso, sin reservas privadas almacenadas ni acciones de pago o reserva habilitadas

#### Scenario: Logout y nueva cuenta
- **WHEN** un paciente cierra sesion y entra otro
- **THEN** ni la vista ni caches persistentes exponen reservas o pagos del anterior

#### Scenario: Navegacion y API homonimas
- **WHEN** se navega a /mis-reservas y se consulta su API JSON, con o sin service worker
- **THEN** la navegacion sirve shell y la API no se reemplaza por HTML ni respuesta privada cacheada

### Requirement: Interfaz movil y accesible
La PWA SHALL funcionar a 360px y desktop sin scroll horizontal para completar tareas, con labels, foco visible, operacion por teclado, botones tactiles y mensajes no dependientes solo del color. Errores y estados de carga SHALL anunciarse accesiblemente, sin datos reales en pruebas o capturas.

#### Scenario: Reserva desde movil
- **WHEN** se completa seleccion e ingreso a 360px
- **THEN** controles y resumen son legibles y utilizables sin ocultar la accion principal

#### Scenario: Acciones con teclado
- **WHEN** se navega formularios y se recibe un error de negocio usando teclado
- **THEN** el foco es visible y el mensaje esta asociado al control o region de estado correspondiente
