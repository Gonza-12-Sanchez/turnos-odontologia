# Proposal

## Why

El backend ya ofrece agenda, gestión y catálogo, pero la PWA solo tiene pantallas
públicas/paciente. El equipo necesita operar desde móvil y escritorio sin usar
Swagger, preservando RBAC, ventana de cancelación y trazabilidad.

## What Changes

- Agregar `/agenda` para secretaria/odontólogo y `/config` para secretaria;
  filtros, estados, tolerancia, sobreturnos y acciones con confirmación explícita.
- Agregar `/cobros` para secretaria: registro incremental, conciliación, override
  auditado y aviso «sin factura electrónica en v1», condicionado a corregir y
  verificar contratos C-09; no activar checkout ni pagos reales.
- Reutilizar sesión y cliente C-10; navegación por rol, retorno interno seguro,
  aislamiento entre cuentas, sin cache ni cola de escrituras privadas.
- Mostrar historial de cambios solo desde registros reales autorizados. El
  backend observado no expone historial por turno: es una dependencia explícita,
  no un dato que la UI pueda inventar a partir de updated_at/origen.
- Avanzar por slices independientes: contratos y UI de agenda/config pueden
  prepararse sin esperar todo C-10. Fecha AR/UTC, permisos de acciones, historial,
  contexto consultorio y cobros tienen gates individuales antes de aceptación.
- Aplicar la política elegida el 2026-11-10: sistema visual y mockups aprobados
  antes de implementar; conservar estética existente, sin rebranding.

## Capabilities

### New Capabilities

- `consultorio/gestion-pwa`: experiencia operativa autenticada del consultorio:
  navegación, agenda/gestión, configuración, cobros locales, historial y privacidad.

### Modified Capabilities

Ninguna. Se consumen `agenda/agenda-mis-reservas`, `agenda/gestion-turnos`,
`agenda/catalogo-config` y `cobros/registro` sin rebajar sus requisitos existentes.
Las discrepancias de implementación son prerrequisitos correctivos, no cambios
de reglas ni autorización implícita para modificar backend.

## Impact

- Futuro código: `frontend/src/App.tsx`, `features/auth/AuthPage.tsx`,
  `shared/api/`, nuevas `features/agenda`, `features/config`, `features/cobros`,
  estilos y pruebas. React 18/Router 6/Vite 6; sin nuevas dependencias previstas.
- Fundación portable en `design-system/`, sin cambiar aún el frontend productivo.
- Dependencias archivadas: C-04, C-06, C-07 y C-09. C-10 no bloquea todo C-11;
  se reutiliza su sesión y se conserva su regresión. C-09 archivado no equivale
  a aceptación monetaria; gates detallados en design/tasks.
- Fuera de alcance: correctivos backend implementados sin aprobación separada,
  migraciones, nuevas reglas de cobro, checkout MP, HCE, ARCA, nuevos usuarios
  staff, automatizar ausencias, infraestructura y C-12. C-11 no se archiva con
  una pantalla de cobros deshabilitada o datos de auditoría ficticios.
