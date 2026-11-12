## Why

El piloto de una sede necesita una instalación reproducible y evidencia de que los flujos críticos resisten errores y concurrencia.

## What Changes

- Arranque local de API, PostgreSQL, Redis y PWA con migraciones automáticas y comprobaciones de salud.
- Regresión de agenda, cobros e integraciones con datos ficticios y servicios externos controlados.
- Medición de higiene de agenda y guía de aceptación del piloto.

## Capabilities

### New Capabilities
- `platform/pilot-readiness`: arranque verificable y criterios de aceptación del piloto.

### Modified Capabilities
- Ninguna.

## Impact

Compose, CI, pruebas, observabilidad y documentación. El archivo final requiere aceptación de C-08, C-10 y C-11, y decisiones de producto sobre WhatsApp y seña.
