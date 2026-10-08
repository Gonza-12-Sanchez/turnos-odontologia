# turnos-odontologia — Base de Conocimiento

Base de conocimiento generada en modo **ingest** desde `docs/discovery/checklist-discovery.md`, `docs/discovery/sources/` (6 notas), `docs/discovery/informe-discovery.md` y `state.discovery`. Sin preguntas (fire-and-forget); dudas en `10_preguntas_abiertas.md`.

## Índice de Archivos

| Archivo | Contenido |
|---------|-----------|
| [01_vision_y_objetivos.md](01_vision_y_objetivos.md) | Propósito, objetivos por actor, alcance v1, fuera de alcance, métricas |
| [02_descripcion_general.md](02_descripcion_general.md) | Stack (a definir), arquitectura mínima, integraciones, API REST |
| [03_actores_y_roles.md](03_actores_y_roles.md) | Paciente/odontólogo/secretaria, matriz RBAC, rutas públicas |
| [04_modelo_de_datos.md](04_modelo_de_datos.md) | Dominios agenda/personas/cobros, ERD, 8 entidades, seed ficticio |
| [05_reglas_de_negocio.md](05_reglas_de_negocio.md) | RN-TU/RN-AU/RN-NT/RN-CO/RN-GL con códigos de trazabilidad |
| [06_funcionalidades.md](06_funcionalidades.md) | 4 épicas, US-001 a US-007 con criterios y reglas |
| [07_flujos_principales.md](07_flujos_principales.md) | Reserva, confirmación WA, agenda del día, cobro local |
| [08_arquitectura_propuesta.md](08_arquitectura_propuesta.md) | Patrones, directorios, seguridad, env vars (a validar) |
| [09_decisiones_y_supuestos.md](09_decisiones_y_supuestos.md) | DD-01 a DD-05 + SU-01 a SU-03 |
| [10_preguntas_abiertas.md](10_preguntas_abiertas.md) | 3 entradas discovery + IN-10-01 a 04 + tabla priorizada |

## Quick Start para Desarrolladores

1. Entender el dominio → [01](01_vision_y_objetivos.md), [03](03_actores_y_roles.md)
2. Entender los datos → [04](04_modelo_de_datos.md)
3. Entender las reglas → [05](05_reglas_de_negocio.md)
4. Entender la arquitectura → [02](02_descripcion_general.md), [08](08_arquitectura_propuesta.md)
5. Implementar → [07](07_flujos_principales.md), [06](06_funcionalidades.md)
6. Antes de codificar → [10](10_preguntas_abiertas.md)

## Resumen Ejecutivo

Sistema de turnos para consultorios odontológicos chicos (1–3 sillones, Argentina): reserva online, agenda multi-sillón con anti-solapamiento garantizado a motor, confirmación automática por WhatsApp y cobro simple. Stack: FastAPI + React/TS/Vite + PostgreSQL + Redis + Docker (DD-06); 2 bloqueantes de Alta prioridad en `10_preguntas_abiertas.md` antes del roadmap.
