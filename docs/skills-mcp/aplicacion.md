# Informe de Aplicación — Skill propia y Servidor MCP

**Proyecto:** turnos-odontologia · **Change de aplicación:** C-02 `core-models` · **Fecha:** 2026-10-28

## 1. Resultados

- **Skill propia `turnos-core-guardian`** integrada a la fundación: registrada en `.atl/skill-registry.md` (trigger + compact rules) y documentada en `AGENTS.md` (cuándo usarla, qué necesita, cómo revisar el resultado). Verificada cargando la skill en una sesión nueva (SKILL.md + references + script accesibles).
- **MCP PostgreSQL** configurado y operativo: `opencode mcp list` → `postgres connected`. Invocación real ejecutada con `postgres_query` (resultado: `db: turnos_test · usuario: turnos · PostgreSQL 17.10`).
- **Change C-02 preparado** (no implementado): artefactos OPSX completos y validados (`proposal.md`, `design.md`, `specs/core/models/spec.md`, `tasks.md`). `openspec status` → `isPlanningComplete: True`. Roadmap (`CHANGES.md`) actualizado marcando C-02 como preparado.

## 2. Enlaces a evidencias

- Invocación MCP: [`evidencias/mcp-postgres-invocacion.md`](evidencias/mcp-postgres-invocacion.md)
- Invocación skill + revisión crítica: [`evidencias/skill-guardian-invocacion.md`](evidencias/skill-guardian-invocacion.md)
- Ficha de investigación: [`investigacion.md`](investigacion.md)
- Configuración MCP (sin secretos): [`mcp-postgres.opencode.example.json`](mcp-postgres.opencode.example.json)

## 3. Archivos modificados y motivo

| Archivo | Motivo |
|---|---|
| `.atl/skill-registry.md` | Registrar `turnos-core-guardian` (trigger, ruta, compact rules) para que el orquestador la inyecte en sub-agentes. |
| `AGENTS.md` | Agregar la skill propia a Backend Core y documentar el MCP PostgreSQL (propósito, capacidades, cuándo usarlo, límites). |
| `README.md` | Documentar requisitos, comprobación y solución de problemas del MCP para reproducibilidad. |
| `CHANGES.md` | Marcar C-02 como preparado (artefactos OPSX listos) sin marcarlo implementado. |
| `openspec/changes/2026-10-27-c-02-core-models/*` | Artefactos del change: proposal, design, specs (≥3 escenarios), tasks. |
| `.agents/skills/turnos-core-guardian/scripts/check_turnos_invariants.py` | Corregir omisión: detectar `Column(DateTime)`/`mapped_column(DateTime)` sin `timezone=True` (revisión crítica). |

## 4. Revisión crítica

**Omisión detectada:** el script de la skill solo detectaba `DateTime()` vacío, pero no `Column(DateTime)` naive (falso negativo). Se detectó creando un archivo de prueba y observando que el script reportaba "OK" ante un error real. La regla dura de `AGENTS.md` ("NUNCA fechas naive") permitió identificarlo. **Corrección:** se agregaron patrones para `Column(DateTime)`/`mapped_column(DateTime)` y una heurística por línea; re-ejecutado, el script ahora bloquea el caso (ver evidencia). Tras borrar el archivo de prueba, vuelve a "OK parcial".

**Límites reconocidos:** el script es heurístico (regex sobre texto), no análisis AST completo; no detecta fechas naive en variables intermedias ni en migraciones con `sa.DateTime(timezone=False)`. Requiere revisión manual complementaria. El MCP es read-only y depende de un Postgres accesible en `localhost:5432`.

## 5. Limitaciones

- No se implementó C-02 (solo se preparó); la implementación queda para una instancia posterior.
- El MCP se probó contra Postgres 17 local (el compose usa 16); la diferencia de versión no afecta la verificación de conexión, pero el compose sigue siendo la fuente de verdad de versión.
- No se generó video de demostración (fuera del alcance automatizable).
