# Configuración del consultorio — C-04

## Persistencia y migración

La revisión Alembic `002`, dependiente de `001`, agrega únicamente `config_audit`: autor, recurso/id, acción, fecha TIMESTAMPTZ y snapshots JSONB antes/después. Tiene FK al usuario e índices por recurso/fecha y actor/fecha. La auditoría se guarda en la misma transacción que el catálogo; un fallo revierte ambos.

Desde backend, con `DATABASE_URL` apuntando a la base autorizada:

```powershell
python -m alembic upgrade head
```

En una base **turnos_test** descartable, se verifica reversión con `python -m alembic downgrade 001` y luego `python -m alembic upgrade head`. Downgrade elimina la tabla de auditoría y sus eventos; no modifica las tablas núcleo. No ejecutar la reversión sobre datos que deban conservarse. Las pruebas de esta implementación se ejecutaron en una instancia aislada, puerto 55432.

Los eventos no tienen API de modificación o baja y nunca incluyen contraseñas, tokens ni datos de pacientes. El autor y el tiempo provienen del servidor.

## API y permisos

Requiere `Authorization: Bearer <access>` de una **secretaria activa** en todas las operaciones. Anónimo/token inválido/inactivo →401; paciente u odontólogo →403. La API verifica el rol vigente en base, no solo el claim JWT.

| Colección | Campos de alta |
|---|---|
| `/api/config/sillones` | `consultorio_id` UUID existente activo, `nombre` no vacío hasta80 caracteres |
| `/api/config/tratamientos` | `nombre` hasta120 caracteres, `duracion_min` entero positivo, `precio_referencia_centavos` entero nullable ≥0 |
| `/api/config/bloqueos` | `sillon_id` UUID nullable, `desde`, `hasta`, `motivo` hasta120 caracteres |

Cada colección ofrece POST→201 y GET→200. `/{id}` ofrece GET/PATCH→200 y DELETE→204. Id/referencia inexistente →404; input inválido o referencia inactiva al asignarla →422; conflicto de persistencia →409. Los campos desconocidos (incluidos autor/fechas de auditoría) se rechazan.

Listados: `?page=1&page_size=20&activo=true` (defaults), máximo100 por página; respuesta `{items,total,page,page_size}`, orden estable por created_at/id. `activo=false` consulta bajas y GET por id conserva acceso administrativo a inactivos.

PATCH conserva atributos omitidos. Null solo se admite para precio de referencia y sillon_id de bloqueo. Nombres se recortan de espacios. `activo=false` y DELETE hacen baja lógica (`is_active=false`, deleted_at aware), conservando fila y relaciones. Reactivar limpia deleted_at. Bajas o modificaciones sin cambio efectivo no duplican auditoría.

## Sillones

Usar el UUID del consultorio demo existente. Ejemplo de body ficticio (reemplazar el UUID por el del seed local):

```json
{"consultorio_id":"00000000-0000-4000-8000-000000000001","nombre":"Sillón demo"}
```

Desactivar un sillón no elimina ni modifica los turnos históricos asociados.

## Tratamientos y centavos

```json
{"nombre":"Control demo","duracion_min":15,"precio_referencia_centavos":250000}
```

`250000` significa 250000 centavos ARS, nunca un float en pesos. Duración y precio deben caber en INTEGER (máximo2147483647); floats y booleanos se rechazan. `{"precio_referencia_centavos":null}` limpia el precio sin modificar la duración. Cambiar duración/precio/estado de un tratamiento no recalcula inicio/fin de turnos existentes.

## Bloqueos y advertencias

```json
{"sillon_id":null,"desde":"2026-12-01T10:00:00-03:00","hasta":"2026-12-01T11:00:00-03:00","motivo":"Mantenimiento demo"}
```

Null significa todos los sillones; un UUID limita el alcance a uno activo existente. Las fechas requieren zona horaria y hasta>desde, también al combinar un PATCH de un solo extremo con valores anteriores. Intervalos semiabiertos `[desde,hasta)`: turnos adyacentes no se solapan.

POST/PATCH de un bloqueo activo devuelven `warnings:[{"code":"TURNOS_SOLAPADOS","cantidad":N}]` si hay turnos activos no cancelados/ausentes en su alcance, o `[]`. Se guarda el bloqueo y no se alteran turnos. Las advertencias son una observación al momento de la mutación; GET/listado no recalculan advertencias. La disponibilidad que excluye bloqueos corresponde a C-05, y los sobreturnos a C-06.
