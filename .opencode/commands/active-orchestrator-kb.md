---
description: "Run only the Knowledge Base phase (kb-creator) for this project"
---

Use the `skill` tool to invoke the `active-orchestrator` skill with the standalone KB entrypoint (`kb`).

It dispatches `kb-creator` directly. Follow that skill completely (interactive discovery Q&A or ingest from `docs/`). Run ONLY this phase and stop — do not chain into roadmap-generator without a new user request.
