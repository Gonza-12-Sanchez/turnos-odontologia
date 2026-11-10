# Proposal

## Why

US-007 necesita registrar cobros y conciliar senas sin duplicar dinero. El contrato 402 de C-05 sigue siendo un placeholder controlado por el cliente: no hay politica de sena en Tratamiento ni un intento persistente que pueda existir antes del Turno.

## What Changes

- Registrar cobros locales solo por secretaria, conciliacion de sena, advertencia de diferencia y override auditado, sin factura electronica (RN-CO-01/02/03).
- Agregar politica servidor por tratamiento: sena deshabilitada, opcional u obligatoria, con monto fijo en centavos; sin valores comerciales inventados.
- Integrar Checkout Pro mediante adaptador HTTP asincronico, intento persistente, consulta propia de estado y webhook firmado que verifica el pago con MP antes de crear turno y cobro atomicamente.
- Completar 402 con checkout real; conservar 409 con alternativas y 201 sin sena. **BREAKING** semantico: los flags existentes del cliente dejan de determinar si el pago es obligatorio; no pueden omitir la politica servidor.
- Resolver duplicados, carreras, rechazos, timeout e incidencia de pago aprobado sin cupo sin prometer reserva ni perder la trazabilidad del dinero.
- Exigir aprobacion humana del diseno concreto ANTES de codigo productivo, tests de codigo o migraciones. Esta propuesta no concede esa aprobacion.

## Capabilities

### New Capabilities

- `cobros/registro`: registro local, lectura autorizada, conciliacion y auditoria de cobros.
- `cobros/sena-mp`: politica de sena, intentos, Checkout Pro, verificacion e idempotencia de pagos y resolucion de incidencias.

### Modified Capabilities

- `agenda/disponibilidad-reserva`: reemplazar el placeholder 402 por el contrato de intento y checkout, con obligatoriedad decidida por tratamiento en servidor.

## Impact

Dependencia C-05 verificada en `archive/2026-11-04-c-05-disponibilidad-reserva`; C-06 y C-08 tambien archivados para reutilizar gestion y recordatorios. Cambios futuros en `backend/app/{api,cobros,services,schemas,models}`, configuracion de tratamiento, settings y migraciones Alembic. `Cobro.turno_id` hoy es obligatorio y `referencia_mp` no es unica: no se usara Cobro como intento previo al turno. HTTPX ya existe, no se necesita SDK sincronico.

C-10 consume el contrato aqui propuesto; no implementa pagos ni duplica su ownership. Fuera de alcance: UI administrativa de C-11, C-12, ARCA, tarjetas propias, marketplace/OAuth multi-vendedor y reembolsos automaticos. Las politicas comerciales, compensacion manual y seams TDD deben aprobarse antes de aplicar. No se requieren credenciales para planificar ni para futuros tests mock; sandbox y produccion tienen gates separados.
