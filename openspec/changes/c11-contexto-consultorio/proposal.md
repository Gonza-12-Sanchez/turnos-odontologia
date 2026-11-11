# Proposal

## Why

C-11 no puede crear el primer sillón sin conocer un consultorio autorizado. El
modelo actual no vincula usuario con consultorio; seleccionar el UUID desde otro
sillón o inventarlo impediría el primer alta y produciría asignaciones arbitrarias.

## What Changes

- Exponer a secretaria un contexto administrativo mínimo para la instalación
  de una sede del MVP: el único consultorio activo, solo si es inequívoco.
- Responder sin contexto utilizable cuando no exista uno activo o haya más de
  uno; no escoger arbitrariamente ni asumir soporte multi-sede.
- Conservar el POST de sillones y su validación de consultorio sin cambios de
  permisos; la UI C-11 consumirá este contrato en su tarea 3.4.

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `agenda/catalogo-config`: contexto de consultorio único accesible solo a secretaria.

## Impact

API FastAPI administrativa, consulta de Consultorio, pruebas aisladas y documentación
de contrato. Sin migración, seeds reales, cambios de autenticación ni multi-sede.
El usuario autorizó correctivos mínimos backend para completar C-11 el 2026-11-11.
