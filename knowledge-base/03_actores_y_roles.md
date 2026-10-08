# Actores y Roles

## Actores del sistema

| Actor | Descripción | Cómo interactúa |
|---|---|---|
| Paciente | Persona con turno o que busca reservar; opera desde el celular | PWA: ve libres, reserva, ve Mis reservas, confirma/cancela (con login) |
| Odontólogo / dueño | Profesional del consultorio (1–3 sillones) | PWA: ve agenda del día, atiende según agenda |
| Secretaria | Rol administrativo del consultorio | PWA: confirma/cancela/reprograma, asigna turnos, registra cobros |
| Proveedor WhatsApp | Actor externo (plantillas Meta) | API: envía recordatorios/confirmaciones; devuelve entrega y respuestas |
| Mercado Pago | Actor externo de cobro | API: procesa seña; notifica por webhook |

## RBAC — Matriz de permisos

| Rol → Recurso | Horarios libres | Turno propio | Turno ajeno | Agenda del día | Cobros | Config (sillones, tratamientos, bloqueos) |
|---|---|---|---|---|---|---|
| Anónimo | R | — | — | — | — | — |
| Paciente | R | CRUD propio | — | — | R propios | — |
| Odontólogo | R | R (sus pacientes) | — | R | R | — |
| Secretaria | R | CRUD | CRUD | CRUD | CRUD | CRUD |

R = lectura, CRUD = alta/baja/modificación/lectura según reglas (RN-TU-02 bloquea cancelación < 2 h para todos).

## Rutas públicas

- `/` — landing del consultorio.
- `/horarios` — ver horarios libres (sin login).
- `/login` — ingreso.
- `/registro` — alta de paciente.
- `/webhooks/whatsapp`, `/webhooks/mercadopago` — solo para los proveedores (firmados).

Todo lo demás (`/mis-reservas`, `/agenda`, `/cobros`, `/config`) requiere login + rol.
