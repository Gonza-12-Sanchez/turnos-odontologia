# Evidencia: invocación de la skill `turnos-core-guardian`

**Fecha:** 2026-10-28
**Skill:** `.agents/skills/turnos-core-guardian/` (SKILL.md + references/ + scripts/check_turnos_invariants.py)

## Solicitud realizada

Revisar el diseño del change C-02 (modelos, migración, seeds) contra las reglas duras
(RN-TU-01, RN-CO-03, RN-GL-01/02/03) y ejecutar el script determinista:

```bash
python .agents/skills/turnos-core-guardian/scripts/check_turnos_invariants.py backend/app/models backend/alembic/versions
```

## Resultado obtenido (estado actual, C-02 aún no implementado)

```
OK parcial turnos-core-guardian: sin fechas naive, sin float/money, seeds OK; EXCLUDE aún no presente (C-02 pendiente)
```

La salida "OK parcial" es la esperada porque no hay modelos ni migraciones todavía;
el EXCLUDE aparecerá cuando se implemente C-02.

## Revisión crítica: omisión detectada en el script

**Defecto inicial:** el script solo detectaba `DateTime()` con paréntesis vacíos
(`DateTime()`), pero NO detectaba `Column(DateTime)` ni `mapped_column(DateTime)` sin
`timezone=True`, que en SQLAlchemy 2.x produce columnas `TIMESTAMPTZ`-naive (violación
de la regla dura "NUNCA fechas naive").

**Cómo se detectó:** se creó un archivo de prueba `backend/app/models/_prueba_naive.py`
con `inicio = Column(DateTime)` (sin timezone) y se ejecutó el script; la salida inicial
fue "OK parcial" (no detectó el error). La regla dura de `AGENTS.md` ("NUNCA fechas
naive → siempre TIMESTAMPTZ") permitió identificar la omisión.

**Antes (script v1):** no reportaba `Column(DateTime)` naive → falso negativo.

**Después (script v2):** se agregaron patrones para `Column(DateTime)`, `mapped_column(DateTime)`
y una heurística por línea que reporta `DateTime` sin `timezone=True`. Re-ejecutado sobre
el archivo de prueba:

```
BLOQUEADO por turnos-core-guardian:
 - FECHA-NAIVE Column/mapped_column(DateTime) sin timezone=True: backend\app\models\_prueba_naive.py:10: inicio = Column(DateTime)  # naive: debe bloquearse
 - FECHA-NAIVE DateTime sin timezone=True: backend\app\models\_prueba_naive.py:10: inicio = Column(DateTime)  # naive: debe bloquearse
```

Tras borrar el archivo de prueba, el script volvió a "OK parcial". El script mejorado
queda versionado en `.agents/skills/turnos-core-guardian/scripts/check_turnos_invariants.py`.

## Qué aportó al change

La skill establece la norma (EXCLUDE en motor, TIMESTAMPTZ, centavos, seeds ficticios)
y bloquea código que la viole antes de `/opsx:apply`. La revisión crítica mejoró el
script para cerrar un falso negativo en la detección de fechas naive.
