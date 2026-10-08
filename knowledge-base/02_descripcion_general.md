# Descripción General

> Fuente: `docs/discovery/checklist-discovery.md` + `docs/discovery/informe-discovery.md`. Stack DEFINIDO por el equipo el 2026-10-06 (ver DD-06 en `09_decisiones_y_supuestos.md`).

## Stack tecnológico

| Capa | Tecnologías | Versión mínima |
|---|---|---|
| Frontend | React + TypeScript + Vite (PWA mobile-first) | React 18+, TS 5+, Vite 6+ |
| Backend API | Python + FastAPI | Python 3.12+, FastAPI 0.115+ |
| Auth | JWT (Bearer) | — |
| ORM | SQLAlchemy 2.x (async) | SQLAlchemy 2.0+ |
| Base de datos | PostgreSQL | PostgreSQL 16+ |
| Async / colas | Redis (recordatorios, reintentos WA, webhooks) | Redis 7+ |
| Contenedores | Docker / Docker Compose (api, db, redis, frontend) | Docker 24+ |
| Proveedor WhatsApp | Plantillas aprobadas por Meta (costo por mensaje) — **a elegir** (ver IN-10-02) | — |
| Cobros | Mercado Pago (seña opcional v1) | API vigente MP |

Restricciones heredadas de Discovery: presupuesto acotado, proyecto chico, mobile-first; ecosistema argentino (pesos, Mercado Pago, ARCA en fase 2, WhatsApp).

## Arquitectura general

```
[React SPA (Vite, PWA)] → [FastAPI + JWT por rol] → [PostgreSQL (SQLAlchemy 2.x)]
        │                          │──→ [Redis] (cola: recordatorios, reintentos WA, webhooks)
        │                          │──→ [Proveedor WhatsApp] (recordatorios/confirmación)
        │                          │──→ [Mercado Pago] (seña opcional)
        └──→ (fase 2+) [ARCA] · (fase 3+) [OOSS / HCE]
```

Todo orquestado con Docker Compose (`api`, `db`, `redis`, `frontend`). Un solo despliegue para 1 sede; 3 roles (paciente, odontólogo, secretaria); agenda como recurso central con invariante anti-solapamiento a nivel de motor (RN-TU-01, constraint de exclusión Postgres).

## Integraciones externas

| Servicio | Propósito | Tipo |
|---|---|---|
| WhatsApp (proveedor plantillas Meta) | Recordatorio + confirmación automáticos con botón — única obligatoria v1 | API REST / webhooks (estado de entrega y respuesta) |
| Mercado Pago | Seña opcional para reservar; registro de cobro | SDK / API REST + webhooks de pago |
| ARCA (fase 2) | Facturación electrónica desde el cobro | Web service (modelo listo, no implementado) |
| Google Calendar / OOSS / HCE | Explícitamente NO v1 | — |

## API REST

Recursos principales (FastAPI routers por recurso, auth JWT Bearer salvo rutas públicas):

- `POST /auth/registro|login` — alta y login de paciente, devuelve JWT (RN-AU-01).
- `GET /horarios-libres?sillon=&tratamiento=&fecha=` — disponibilidad pública.
- `POST /turnos` — reservar (aplica RN-TU-01/02/03/04); `PATCH /turnos/{id}/confirmar|cancelar|reprogramar`.
- `GET /agenda?fecha=&sillon=` — agenda diaria (odontólogo/secretaria).
- `GET /mis-reservas` — reservas del paciente logueado.
- `POST /cobros` (+ `POST /pagos/seña`) — cobro simple local y seña MP (RN-CO-01/02).
- `POST /webhooks/whatsapp|mercadopago` — eventos de entrega/respuesta y pagos.
