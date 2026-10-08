---
description: "Regenerate agent rules only (CLAUDE.md / AGENTS.md) via agent-instruction"
---

Use the `skill` tool to invoke the `active-orchestrator` skill with the standalone rules entrypoint (`rules`).

It dispatches `agent-instruction` directly (re-gen of `CLAUDE.md` / `AGENTS.md`). Follow that skill completely — it asks for the project's hard rules interactively, so ask the user and wait. Run ONLY this phase and stop.
