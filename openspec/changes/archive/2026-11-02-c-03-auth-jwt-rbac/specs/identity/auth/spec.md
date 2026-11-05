# Spec Delta — identity/auth

## Purpose

Proveer gestión de identidad y acceso para el sistema de turnos odontológicos: registro de pacientes, autenticación basada en JWT con refresh tokens rotativos, rate limiting, control de acceso basado en roles y una cookie HttpOnly de refresh, para que cada endpoint protegido pueda autenticar usuarios y aplicar la matriz RBAC.

## ADDED Requirements

### Requirement: El registro de paciente crea un usuario y un perfil de paciente

El sistema SHALL exponer `POST /auth/registro` que crea un `Usuario` activo con rol `paciente` y un `Paciente` vinculado en una única transacción, almacenando una contraseña hasheada con bcrypt, un número de teléfono argentino validado y un email único; SHALL devolver HTTP 201 con la representación del usuario creado y SHALL NOT emitir tokens.

#### Scenario: Registro exitoso de paciente (feliz)

- **GIVEN** un payload de registro válido con un email único, una contraseña que cumple la política, un teléfono AR válido y un nombre
- **WHEN** se envía `POST /auth/registro`
- **THEN** el sistema responde HTTP 201 con el usuario creado (id, email, rol `paciente`) y persiste `Usuario` + `Paciente` de forma atómica

#### Scenario: Email duplicado es rechazado (error de negocio)

- **GIVEN** un `Usuario` existente con el email enviado
- **WHEN** se envía `POST /auth/registro`
- **THEN** el sistema responde HTTP 409 y no crea nuevos registros

#### Scenario: Teléfono inválido o contraseña débil es rechazado (borde)

- **GIVEN** un payload de registro con un teléfono no-AR o una contraseña de menos de 8 caracteres o sin una letra y un dígito
- **WHEN** se envía `POST /auth/registro`
- **THEN** el sistema responde HTTP 422 con errores de validación

### Requirement: Login autentica y emite tokens de acceso y refresh

El sistema SHALL exponer `POST /auth/login` que verifica email y contraseña, y en caso de éxito emite un JWT de acceso firmado (tipo `access`) en el cuerpo de la respuesta y un refresh token (tipo `refresh`) en una cookie HttpOnly, registrando una nueva familia de refresh en Redis; ante cualquier fallo de credenciales SHALL responder HTTP 401 con un mensaje genérico que no revele si el email existe.

#### Scenario: Login exitoso (feliz)

- **GIVEN** un usuario activo con email y contraseña válidos
- **WHEN** se envía `POST /auth/login` con credenciales correctas
- **THEN** el sistema responde HTTP 200 con `access_token`, `token_type: bearer` y `expires_in`, y setea la cookie HttpOnly `refresh_token`

#### Scenario: Credenciales inválidas son rechazadas (error de negocio)

- **GIVEN** una solicitud de login con contraseña incorrecta o email desconocido o usuario inactivo
- **WHEN** se envía `POST /auth/login`
- **THEN** el sistema responde HTTP 401 con un error genérico y no emite ningún token

### Requirement: Los JWT de acceso llevan claims estándar y se validan

El sistema SHALL emitir tokens de acceso como JWT HS256 que contienen los claims `sub` (id de usuario), `roles` (array), `email`, `jti` (id único), `type="access"`, `iat` y `exp` gobernados por `JWT_EXPIRE_MINUTES`, y SHALL rechazar toda solicitud que presente un token expirado, malformado, manipulado, que no sea de acceso o esté en blacklist con HTTP 401.

#### Scenario: Token de acceso expirado es rechazado (borde)

- **GIVEN** un token de acceso cuyo `exp` está en el pasado
- **WHEN** se presenta como Bearer a un endpoint protegido
- **THEN** el sistema responde HTTP 401

#### Scenario: Token de acceso en blacklist es rechazado (borde)

- **GIVEN** un token de acceso cuyo `jti` fue revocado (p. ej. tras logout)
- **WHEN** se presenta como Bearer a un endpoint protegido
- **THEN** el sistema responde HTTP 401

### Requirement: Los refresh tokens rotan y los tokens reutilizados revocan la familia

El sistema SHALL exponer `POST /auth/refresh` que lee la cookie de refresh, valida el JWT de refresh y, en caso de éxito, lo rota: agrega a blacklist el `jti` presentado, emite un nuevo token de acceso y un nuevo refresh token bajo el mismo id de familia, y actualiza el registro de familia en Redis. Si se reutiliza un `jti` de refresh que ya está en blacklist, el sistema SHALL eliminar el registro de familia y responder HTTP 401, forzando re-autenticación.

#### Scenario: Rotación exitosa de refresh (feliz)

- **GIVEN** una cookie de refresh válida y no revocada
- **WHEN** se envía `POST /auth/refresh`
- **THEN** el sistema responde HTTP 200 con un nuevo token de acceso, setea una nueva cookie `refresh_token` y el `jti` del refresh anterior queda en blacklist

#### Scenario: Refresh token reutilizado revoca la familia (borde)

- **GIVEN** un refresh token cuyo `jti` ya fue rotado (en blacklist)
- **WHEN** se envía `POST /auth/refresh` con él
- **THEN** el sistema responde HTTP 401 y elimina el registro de familia correspondiente en Redis

#### Scenario: Cookie de refresh ausente o inválida es rechazada (error de negocio)

- **GIVEN** una solicitud sin cookie `refresh_token` válida
- **WHEN** se envía `POST /auth/refresh`
- **THEN** el sistema responde HTTP 401

### Requirement: Logout revoca la sesión actual

El sistema SHALL exponer `POST /auth/logout` que requiere un token de acceso válido y agrega a blacklist el `jti` de acceso, elimina la familia de refresh de Redis, agrega a blacklist el `jti` de refresh si está presente, limpia la cookie de refresh y responde HTTP 204. La operación SHALL ser idempotente respecto a la cookie.

#### Scenario: Logout exitoso (feliz)

- **GIVEN** un usuario autenticado con un token de acceso válido y cookie de refresh
- **WHEN** se envía `POST /auth/logout`
- **THEN** el sistema responde HTTP 204, limpia la cookie y el `jti` de acceso queda en blacklist

#### Scenario: Logout sin token de acceso válido es rechazado (error de negocio)

- **GIVEN** una solicitud sin Bearer de acceso válido
- **WHEN** se envía `POST /auth/logout`
- **THEN** el sistema responde HTTP 401

### Requirement: El endpoint me devuelve el usuario autenticado

El sistema SHALL exponer `GET /auth/me` que requiere un token de acceso válido y devuelve la representación del usuario actual (id, email, rol y nombre/teléfono del paciente cuando corresponda) y responde HTTP 401 cuando no está autenticado.

#### Scenario: Me autenticado (feliz)

- **GIVEN** un token de acceso válido para un usuario activo
- **WHEN** se envía `GET /auth/me`
- **THEN** el sistema responde HTTP 200 con la representación del usuario

#### Scenario: Me no autenticado es rechazado (error de negocio)

- **GIVEN** una solicitud sin Bearer de acceso válido
- **WHEN** se envía `GET /auth/me`
- **THEN** el sistema responde HTTP 401

### Requirement: Los endpoints de autenticación tienen rate limiting

El sistema SHALL aplicar un rate limit de ventana fija de 5 requests por 60 segundos por IP del cliente y email normalizado a `POST /auth/login` y `POST /auth/registro`, respondiendo HTTP 429 con un header `Retry-After` y un cuerpo descriptivo cuando se excede.

#### Scenario: Rate limit excedido devuelve 429 (error de negocio)

- **GIVEN** más de 5 requests desde la misma IP y email dentro de 60 segundos
- **WHEN** se envía otra solicitud a `/auth/login` o `/auth/registro`
- **THEN** el sistema responde HTTP 429 con `Retry-After` y no procesa la solicitud

### Requirement: Las dependencias de control de acceso basado en roles están disponibles

El sistema SHALL proveer las dependencias `get_current_user`, `require_role(*roles)`, `require_admin()` (alias para secretaria) y `get_optional_user` que aplican la matriz RBAC: anónimo solo donde esté explícitamente público, los pacientes son dueños de sus recursos, los odontólogos leen su agenda, secretaria tiene CRUD total; el acceso no autorizado SHALL responder HTTP 401 y el mismatch de rol SHALL responder HTTP 403.

#### Scenario: El paciente no puede acceder a la agenda (borde)

- **GIVEN** un usuario autenticado con rol `paciente`
- **WHEN** solicita un endpoint restringido a `odontologo` o `secretaria` (p. ej. agenda)
- **THEN** el sistema responde HTTP 403

#### Scenario: El anónimo no puede crear turnos (borde)

- **GIVEN** una solicitud sin Bearer token válido
- **WHEN** se envía `POST /turnos`
- **THEN** el sistema responde HTTP 401

### Requirement: Las contraseñas se hashean con bcrypt

El sistema SHALL hashear las contraseñas usando bcrypt con un factor de costo configurable (default 12) y SHALL NOT almacenar ni loguear contraseñas en texto plano; la verificación SHALL usar el mismo esquema y soportar re-hashing transparente.

#### Scenario: La contraseña se almacena hasheada (feliz)

- **GIVEN** un usuario se registra con una contraseña en texto plano
- **WHEN** el registro de usuario se persiste
- **THEN** `password_hash` es un hash bcrypt y el texto plano no se almacena

### Requirement: El refresh token se entrega en una cookie HttpOnly

El sistema SHALL entregar el refresh token en una cookie llamada `refresh_token` con los atributos `HttpOnly`, `Secure` (configurable), `SameSite=lax`, `Path=/auth` y `Max-Age` igual al TTL del refresh; el token de acceso SHALL devolverse en el cuerpo de la respuesta y nunca en una cookie.

#### Scenario: Los atributos de la cookie de refresh se setean (feliz)

- **GIVEN** un login o refresh exitoso
- **WHEN** se envía la respuesta
- **THEN** el header `Set-Cookie` contiene `refresh_token` con `HttpOnly`, `Secure`, `SameSite=Lax`, `Path=/auth`

### Requirement: Las credenciales de usuario son únicas por email y teléfono

El sistema SHALL aplicar unicidad de `Usuario.email` (case-insensitive, indexado) y de los números de teléfono del paciente en la capa de servicio, respondiendo HTTP 409 en caso de conflicto; el email SHALL normalizarse a minúsculas.

#### Scenario: El email se normaliza y es único (feliz)

- **GIVEN** un registro con email `User@Example.com`
- **WHEN** se crea la cuenta
- **THEN** se almacena como `user@example.com` y un segundo registro con el mismo email (en cualquier casing) es rechazado con HTTP 409
