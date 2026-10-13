# Evidencia Engram — Etapa 7 (turnos-odontologia)

> Archivo de evidencia, sin commit. Proyecto: `turnos-odontologia`.

## 1. Qué es Engram y qué guarda de este proyecto

Engram es la memoria persistente del agente entre sesiones: guarda **decisiones, bugfix, arquitectura y discovery** con título, tipo, contenido (What/Why/Where/Learned), fecha y proyecto. Permite que otro agente (o el mismo, en otra sesión) recupere contexto sin repreguntar.

Observaciones reales citadas (IDs verificados vía `mem_search` / `mem_get_observation`):

- **#30 [decision] «OPSX: entrega lista para commit usuario» (2026-10-08):** README corregido (path archive + `cd ..`), tests C-01 en verde (backend 4/4, frontend 3/3, tsc y `compose config` PASS), sin secretos, PDF con paridad A–D+Verificación. El usuario hace los commits.
- **#29 [decision] «OPSX: limpieza discovery y gitignore completada» (2026-10-08):** referencias `discovery/` re-apuntadas a `docs/discovery/` (informe + README + KB), PDF regenerado con reportlab (6 págs), borrada `discovery/` raíz, checklist unificado, bloque Python en `.gitignore`. Sin commit.
- **#28 [decision] «OPSX: versionado atl y consolidación discovery sin commit» (2026-10-08):** usuario decidió C-01 como change definitivo, **no crear CLAUDE.md**, versionar `.atl/skill-registry.md` (fix `.gitignore` con `.atl/*` + excepción), consolidar solo `docs/discovery/`.
- **#5 [discovery] «OPSX: discovery completado para turnos-odontologia» (2026-09-29):** discovery de 11 puntos + 18 sistemas (tabla, matriz ponderada, recomendación MVP). Gap real: duración variable + WhatsApp incluido + lista de espera multi-sillón barata.
- **#10 [discovery] «Informe Discovery completo + PDF gemelo» (2026-10-05):** `docs/discovery/informe-discovery.md` + PDF gemelos (secciones A–D + Verificación de fuentes). Aprendizaje: fpdf2 falla con tablas largas → usar reportlab; PowerShell 5.1 rompe `python -c` con backslashes.
- **#19 [session_summary] «Session summary: turnos-odontologia» (2026-10-06):** fundación Active Stack de step discovery hasta step done (KB 10+README con stack FastAPI+React, CHANGES.md 12 changes/6 fases, 14 skills, registry, AGENTS.md+CLAUDE.md). Pendientes: IN-10-03 / IN-10-02-04.

Tipos cubiertos con estas 6 citas: `decision` (#30, #29, #28), `discovery` (#5, #10), `session_summary` (#19); el historial además incluye `bugfix` (C-01 8/10 → 10/10 verificado en Docker) y `architecture` (KB FastAPI+React, roadmap CHANGES.md).

## 2. Consulta real de recuperación

Query documentada (ejecutada 2026-10-08):

```text
mem_search: "discovery turnos odontologia" (proyecto turnos-odontologia)
→ 10 resultados
```

Resultado real obtenido:

| # | Tipo | Título |
|---|------|--------|
| 5 | discovery | OPSX: discovery completado para turnos-odontologia |
| 1 | discovery | Scrape Oclusar para Discovery turnos-odontologia |
| 3 | discovery | Discovery Latam 6 sistemas turnos odontología |
| 6 | session_summary | Session summary: turnos-odontologia |
| 2 | discovery | Discovery mercado intl odontología - 6 sistemas |
| 4 | discovery | Discovery mercado AR odontología - 6 adicionales |
| 19 | session_summary | Session summary: turnos-odontologia |
| 30 | decision | OPSX: entrega lista para commit usuario |
| 28 | decision | OPSX: versionado atl y consolidación discovery sin commit |
| 10 | discovery | Informe Discovery completo + PDF gemelo |

Esto cubre lo pedido: checklist/scrape Oclusar (#1), 6 AR adicionales (#4), 6 Latam (#3), 6 intl (#2), informe+PDF (#10) y session summaries (#6, #19).

**Cómo evita arrancar de cero:** un agente nuevo recupera sin repreguntar que el stack es **FastAPI + JWT + SQLAlchemy + Postgres + Redis + Docker / React + TS + Vite**, que **C-01 está archivado 10/10** (spec sincronizado en `openspec/specs/platform/health/spec.md`), y las decisiones **«no crear CLAUDE.md»** y **«solo `docs/discovery/`»** (#28/#29). También recupera gotchas (openspec vía `cmd /c`, PDF con reportlab, `Get-FileHash` en vez de `diff`).
