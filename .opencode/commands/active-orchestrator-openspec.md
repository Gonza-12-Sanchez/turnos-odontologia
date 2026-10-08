---
description: "Run openspec init only (scaffold openspec/ in this project)"
---

Use the `skill` tool to invoke the `active-orchestrator` skill with the standalone OpenSpec entrypoint (`openspec`).

It runs `openspec init` only (plus cleanup of redundant `openspec-*` skill copies). If `openspec/` already exists, ask "Reusarlo o regenerar" and wait. Run ONLY this step and stop.

Windows note: run any `openspec ...` CLI call via `cmd /c "openspec ..."` — direct invocation fails under PowerShell 5.1 ExecutionPolicy.
