# Spec — platform/health

## Purpose

Expone el estado agregado del sistema (API + PostgreSQL + Redis) para que el deploy, C-12 y cualquier operador verifiquen de forma observable que la plataforma está levantada y qué dependencia falla.

## Requirements

### Requirement: Health endpoint reports aggregated status

The system SHALL expose `GET /api/health` returning HTTP 200 with a body containing `status` (`ok` when every check is up, `degraded` otherwise) and a `checks` object with the state of `db` and `redis`. The endpoint itself SHALL never fail because of a failing check.

#### Scenario: Sistema completamente levantado (feliz)

- **GIVEN** la API está levantada con PostgreSQL y Redis alcanzables
- **WHEN** se pide `GET /api/health`
- **THEN** responde HTTP 200 con `status: ok` y `checks: {db: up, redis: up}`

#### Scenario: Redis caído degrada sin tumbar el endpoint (error)

- **GIVEN** Redis no responde pero PostgreSQL sí
- **WHEN** se pide `GET /api/health`
- **THEN** responde HTTP 200 con `status: degraded` y `checks.redis: down` (nunca 500 por el check)

#### Scenario: Chequeo lento se declara caído pasado el timeout (borde)

- **GIVEN** un check tarda más que el timeout configurado en responder
- **WHEN** se pide `GET /api/health`
- **THEN** ese check se reporta `down`, el `status` global es `degraded` y el tiempo total de respuesta queda acotado por el timeout

### Requirement: Health endpoint is public

The system SHALL serve `GET /api/health` without authentication.

#### Scenario: Acceso anónimo al health check

- **GIVEN** un cliente sin token JWT
- **WHEN** se pide `GET /api/health`
- **THEN** responde HTTP 200 igual que un cliente autenticado (nunca 401 por falta de token)
