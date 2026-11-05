# Invariantes núcleo (RN-TU / RN-CO / RN-GL)

Checklist para C-02, reutilizable en C-04/C-05/C-06.

## Turnos

- **RN-TU-03**: `fin = inicio + tratamiento.duracion_min`. `fin` se calcula en backend, jamás viene del cliente. `duracion_min INT > 0`.
- **RN-TU-04**: todo turno tiene `sillon_id NOT NULL`. Disponibilidad siempre por sillón.
- **RN-TU-06**: `Bloqueo(sillon_id NULL = todos, desde, hasta, motivo)`. Sobreturno solo `rol=secretaria` + `es_sobreturno=true + motivo`, marcado en respuesta.
- **RN-TU-02** (recordar para C-06): cancelar/reprogramar con `< APPOINTMENT_CANCEL_MINUTES (120)` → 422 para todos. Solo backend decide.

## Cobros (RN-CO-03)

- `monto_centavos INTEGER >= 0`, moneda ARS implícita. Prohibido `Float`, `Numeric` con decimales de peso, y tipo `money`.
- Ejemplo: `$1.500,00` → `150000` centavos. El script bloquea `Column(Float)` y `money`.

## Auditoría y origen (RN-GL-03)

- `AuditMixin`: `is_active bool`, `created_at/updated_at TIMESTAMPTZ`, `deleted_at nullable`.
- `Turno.origen IN (online, mostrador, whatsapp)`. Cada transición guarda quién/cuándo/origen.
- Soft delete: desactivar sillón (`is_active=false`) no borra turnos históricos.

## Datos ficticios (RN-GL-02)

- Seeds permitidos: "Consultorio demo", "Sillón 1/2", Limpieza 30 min, Control 15 min, Conducto 60 min, `paciente.prueba+...@example.com`, tel `+54 9 11 0000-0000`.
- Bloquear: DNI reales, nombres reales, teléfonos reales, emails personales, `obra_social` con datos sensibles.

## Teléfono AR

Validar en Pydantic/servicio con regex `^\+54\s?9?\s?\d{2,4}[\s-]?\d{6,8}$` (flexible), no con CHECK SQL críptico.

## Matriz rápida para el reporte

| Regla | Dónde mirar | Falla si |
|---|---|---|
| fin calculado | `services/*reserva*`, `models/turno*` | `fin` viene del schema de entrada |
| centavos | `models/cobro*`, migración | `Float` / `money` |
| TIMESTAMPTZ | modelos + migración | `DateTime()` sin `timezone=True` |
| EXCLUDE parcial | migración + modelo | falta `WHERE` o `btree_gist` |
| seeds ficticios | `seeds/*`, `alembic/*data*` | email/tel real |
