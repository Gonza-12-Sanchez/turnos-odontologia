# Arquitectura Propuesta

> Stack definido el 2026-10-06 (DD-06): FastAPI + SQLAlchemy + PostgreSQL + Redis + Docker atrás; React + TS + Vite adelante. Invariantes no negociables: RN-TU-01 y RN-TU-02 a nivel de motor (RN-GL-01).

## Patrones aplicados

| Patrón | Dónde se usa | Por qué |
|---|---|---|
| Capas (API → servicio → persistencia) | Backend | Invariantes de agenda testeables sin UI |
| Constraint de exclusión en rango | Tabla Turno | Anti-solapamiento garantizado por motor, no por UI |
| Idempotencia por clave externa | Webhooks WA/MP | Reintentos de proveedores no duplican efectos |
| RBAC por rol | Toda la API | 3 roles con matriz explícita (03) |
| PWA mobile-first | Frontend | Uso entre paciente y paciente / desde el celular |

## Estructura de directorios

```
turnos-odontologia/
├── knowledge-base/      # esta KB (no se versiona código acá)
├── openspec/            # specs y changes
├── docker-compose.yml   # api + db (postgres:16) + redis:7 + frontend
├── backend/             # Python + FastAPI
│   ├── app/
│   │   ├── api/         # routers: auth, turnos, agenda, cobros, webhooks
│   │   ├── services/    # agenda (disponibilidad, invariantes RN-TU-*)
│   │   ├── workers/     # notificaciones WhatsApp vía Redis
│   │   ├── cobros/      # registro + Mercado Pago
│   │   └── db/          # modelos SQLAlchemy 2.x + migraciones + seeds ficticios
│   └── tests/           # feliz + error de negocio + borde (Etapa 6)
└── frontend/            # React + TS + Vite (PWA)
    └── src/
        ├── features/    # reserva, agenda, mis-reservas, cobros
        ├── shared/      # api client (JWT), ui
        └── pages/       # /, /horarios, /login, /registro, /agenda…
```

## Seguridad

- Autenticación: JWT Bearer; login paciente obligatorio para reservar (RN-AU-01); passwords con hash (bcrypt/argon2); esquema password vs OTP-WhatsApp a decidir (IN-10-03).
- Autorización: RBAC por rol según matriz (03) como dependencias FastAPI; anon solo lectura de libres.
- Validación de input: schemas Pydantic + teléfono AR, ventanas de 2 h y rangos en backend (RN-GL-01).
- Secrets management: credenciales WA/MP/JWT solo por variables de entorno; jamás en repo.

## Variables de entorno

| Variable | Descripción | Ejemplo | Sensible |
|---|---|---|---|
| `DATABASE_URL` | Conexión PostgreSQL | `postgresql+asyncpg://user:***@db:5432/turnos` | Y |
| `REDIS_URL` | Cola y reintentos | `redis://redis:6379/0` | N |
| `JWT_SECRET_KEY` | Firma de tokens | `***` | Y |
| `JWT_EXPIRE_MINUTES` | Expiración del access token | `60` | N |
| `WHATSAPP_PROVIDER` | Proveedor plantillas Meta | `proveedor-x` | N |
| `WHATSAPP_API_KEY` | Credencial proveedor | `***` | Y |
| `MP_ACCESS_TOKEN` | Credencial Mercado Pago | `***` | Y |
| `FRONTEND_URL` | Origen permitido (CORS) | `http://localhost:5173` | N |
| `APPOINTMENT_CANCEL_MINUTES` | Ventana mínima cancelación | `120` | N |
| `LATE_TOLERANCE_MINUTES` | Tolerancia visible | `5` | N |
