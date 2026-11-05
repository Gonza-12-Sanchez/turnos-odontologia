# Spec Delta — identity/auth

## MODIFIED Requirements

### Requirement: Las contraseñas se hashean con bcrypt

El sistema SHALL hashear contraseñas con bcrypt y costo configurable (default 12), sin almacenar ni loguear texto plano. SHALL rechazar registros de más de 72 bytes UTF-8 con 422, sin truncar, y mantener mínimo 8 caracteres, letra y dígito. SHALL verificar hashes existentes y actualizar transparentemente un costo inferior al configurado después de un login válido, sin reducir costos mayores.

#### Scenario: La contraseña se almacena hasheada (feliz)

- **GIVEN** un usuario se registra con una contraseña en texto plano
- **WHEN** el registro de usuario se persiste
- **THEN** `password_hash` es un hash bcrypt y el texto plano no se almacena

#### Scenario: Límite de bytes validado antes de hashear

- **WHEN** se registra una contraseña válida de 72 bytes UTF-8 o una de 73 bytes
- **THEN** la primera es aceptada y la segunda recibe 422 sin crear usuario ni truncar la contraseña

#### Scenario: Caracteres multibyte cuentan por bytes

- **WHEN** una contraseña cumple mínimo, letra y dígito pero excede 72 bytes UTF-8 aunque tenga menos de 72 caracteres
- **THEN** el registro responde 422

#### Scenario: Login actualiza un costo bcrypt antiguo

- **GIVEN** un hash bcrypt válido con costo inferior al configurado
- **WHEN** el usuario inicia sesión con su contraseña correcta
- **THEN** el login es exitoso y se persiste un hash con el costo actual que verifica la misma contraseña

### Requirement: Los JWT de acceso llevan claims estándar y se validan

El sistema SHALL emitir JWT access HS256 con `sub`, `roles`, `email`, `jti`, `type`, `iat` y `exp` según JWT_EXPIRE_MINUTES. SHALL exigir esos claims y sus tipos válidos, UUID de sub/jti, roles conocidos y tiempos coherentes. Tokens expirados, incompletos, malformados, manipulados, de otro tipo o revocados SHALL recibir 401.

#### Scenario: Token de acceso expirado es rechazado (borde)

- **GIVEN** un token de acceso cuyo `exp` está en el pasado
- **WHEN** se presenta como Bearer a un endpoint protegido
- **THEN** el sistema responde HTTP 401

#### Scenario: Token de acceso en blacklist es rechazado (borde)

- **GIVEN** un token de acceso cuyo `jti` fue revocado (p. ej. tras logout)
- **WHEN** se presenta como Bearer a un endpoint protegido
- **THEN** el sistema responde HTTP 401

#### Scenario: Claims ausentes o inválidos no permiten autenticarse

- **WHEN** se presenta un JWT firmado sin un claim obligatorio, con jti/sub no UUID, roles de tipo incorrecto o timestamps booleanos/incoherentes
- **THEN** la ruta protegida responde 401 y no permite evitar la revocación

#### Scenario: Refresh no sirve como access

- **WHEN** se presenta un refresh token válido como Bearer en `/auth/me`
- **THEN** el sistema responde 401

### Requirement: Los refresh tokens rotan y los tokens reutilizados revocan la familia

El sistema SHALL validar la cookie de `/auth/refresh` y rotar de forma indivisible: revocar el jti anterior, emitir access y refresh nuevos en la misma familia y actualizar su registro. La reutilización SHALL revocar la familia y responder 401. Solicitudes concurrentes SHALL NOT rotar exitosamente el mismo token dos veces ni restaurar una familia eliminada por logout.

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

#### Scenario: Reutilización invalida el refresh recién emitido

- **GIVEN** un refresh rotado exitosamente y su reemplazo
- **WHEN** se reutiliza el anterior y luego se intenta usar el reemplazo
- **THEN** ambos intentos responden 401 porque la familia fue revocada

#### Scenario: Rotaciones concurrentes no producen dos sesiones vigentes

- **WHEN** dos solicitudes simultáneas intentan rotar el mismo refresh válido
- **THEN** como máximo una responde 200, la otra responde 401 y la familia queda revocada por reutilización

#### Scenario: Claims de refresh incompletos o tipo equivocado

- **WHEN** la cookie contiene un access token o un refresh sin fid/jti/sub/iat/exp/roles/email válidos
- **THEN** `/auth/refresh` responde 401 sin modificar familias válidas

### Requirement: Los endpoints de autenticación tienen rate limiting

El sistema SHALL limitar `/auth/login` y `/auth/registro` a 5 requests por 60 segundos por IP confiable del cliente y email normalizado. Contador y expiración SHALL actualizarse indivisiblemente. Exceder el límite SHALL devolver 429 con Retry-After. Headers de IP suministrados directamente por un cliente SHALL NOT permitir cambiar su identidad de rate limit.

#### Scenario: Rate limit excedido devuelve 429 (error de negocio)

- **GIVEN** más de 5 requests desde la misma IP y email dentro de 60 segundos
- **WHEN** se envía otra solicitud a `/auth/login` o `/auth/registro`
- **THEN** el sistema responde HTTP 429 con `Retry-After` y no procesa la solicitud

#### Scenario: Header de IP falsificado no evade límite

- **WHEN** un cliente envía seis requests con el mismo email cambiando X-Forwarded-For en cada uno sin pasar por un proxy confiable
- **THEN** el sexto request responde 429

#### Scenario: Ventana expira incluso bajo concurrencia

- **WHEN** varios requests inician simultáneamente una ventana de rate limit
- **THEN** todos comparten un contador con expiración finita y el cliente puede intentar nuevamente al expirar la ventana

## ADDED Requirements

### Requirement: La indisponibilidad del almacenamiento de sesiones falla de forma controlada

El sistema SHALL responder 503 genérico cuando Redis no permita comprobar o persistir revocaciones, familias o límites. SHALL NOT autenticar omitiendo controles ni devolver éxito en una operación de sesión fallida.

#### Scenario: Error Redis durante autenticación

- **WHEN** Redis falla durante login, refresh, logout o validación de un access token que requiere consulta de revocación
- **THEN** la operación responde 503 sin exponer detalles internos ni permitir acceso sin los controles requeridos
