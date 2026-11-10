# Proposal

## Why

Las APIs de disponibilidad y Mis reservas estan archivadas pero el frontend solo muestra Home, sin rutas ni sesion. US-001/002/003 requieren un flujo movil completo que preserve las reglas servidor y no filtre datos personales en caches PWA.

## What Changes

- Crear las paginas `/`, `/horarios`, `/login`, `/registro`, `/mis-reservas` y `/pagos/retorno` para paciente, sin pantallas administrativas.
- Agregar una proyeccion publica minima de sillones y tratamientos activos para los filtros; no abrir `/api/config`, hoy exclusivo de secretaria.
- Completar cliente tipado con PATCH, cookies de auth, cuerpo de error seguro y sesion con access token solo en memoria; registro seguido de login explicito, refresh coordinado y logout.
- Reservar con 201, mostrar alternativas en 409 y consumir el checkout 402 de C-09; retorno MP nunca equivale a pago confirmado.
- Mostrar reservas propias, tolerancia y confirmar/cancelar segun acciones servidor y errores 422.
- Completar instalabilidad PWA y shell offline sin cache de APIs, datos privados ni cola de escrituras.
- Exigir strict TDD posterior a aprobacion de seams y solicitud separada de implementacion.

## Capabilities

### New Capabilities

- `agenda/catalogo-publico`: proyeccion publica allowlist de catalogo activo necesaria para reservar.
- `paciente/reserva-pwa`: navegacion publica y de paciente, sesion cliente, reserva, Mis reservas y PWA segura.

### Modified Capabilities

Ninguna: se consumen identity/auth, agenda/disponibilidad-reserva, agenda/gestion-turnos y agenda/agenda-mis-reservas sin cambiar sus permisos ni reglas.

## Impact

Dependencias C-05 y C-07 verificadas en `archive/2026-11-04-c-05-disponibilidad-reserva` y `archive/2026-11-05-c-07-agenda-mis-reservas-api`. C-03/C-06 archivados suministran auth y acciones. CHANGES.md contradice su arbol respecto de C-09: la seccion C-10 lista solo C-05/C-07, pero 402 real necesita C-09. Planificacion conjunta permitida; aceptacion integrada de pago bloqueada hasta C-09 aprobado, implementado y contrato verificado (preferentemente archivado).

Cambios futuros en `frontend/src/{pages,features,shared}`, `vite.config.ts`, assets de manifest, dependencias de rutas/pruebas y un endpoint backend publico de solo lectura. El cliente actual solo tiene GET/POST y pierde cuerpos de error; faltan router, pruebas DOM/E2E e iconos declarados. Se mantiene React 18/Vite 6, no se migra stack. La politica y persistencia de pagos son propiedad exclusiva de C-09. Fuera de alcance C-11/C-12, agenda profesional, cobros/config administrativos, reprogramacion UI y facturacion. Esta entrega solo crea artefactos, no codigo ni tests.
