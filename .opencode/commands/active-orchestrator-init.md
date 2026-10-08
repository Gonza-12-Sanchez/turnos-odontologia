---
description: Retomar o iniciar la fundación Active Stack (OpenSpec + Discovery + KB + Roadmap + Skills + Reglas)
---

Retomá la fundación del proyecto con el orquestador Active Stack.

**Precondición:** este comando debe ejecutarse con el repositorio del proyecto
(`turnos-odontologia`) como directorio de trabajo. Si no hay `.active-orchestrator-state.json`
ni `openspec/` en el directorio actual, avisá y no inventes nada.

**Windows/PowerShell:** el CLI `openspec` falla con ExecutionPolicy si se lo invoca
directo en PowerShell 5.1. Ejecutá todos los comandos `openspec ...` vía
`cmd /c "openspec ..."` (ej.: `cmd /c "openspec --version"`).

**Pasos:**

1. Usá la herramienta Skill para invocar `active-orchestrator`.
2. Seguí esa skill al pie de la letra: primero la lógica de resume
   (si `.active-orchestrator-state.json` existe con `step != "done"`, preguntar
   "Continuar desde `{step}` o empezar de cero"), después el flujo que corresponda.
3. Respetá el protocolo de checkpoints: parar después de cada fase y esperar
   la decisión del usuario (Continuar / Ajustar / Parar acá) antes de avanzar `step`.
