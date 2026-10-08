---
description: "Rebuild .atl/skill-registry.md after installing or removing skills"
---

Use the `skill` tool to invoke the `active-orchestrator` skill with the standalone registry entrypoint (`registry`).

It dispatches `skill-registry` directly: scan the installed skills, rebuild `.atl/skill-registry.md`, write the state section. Run ONLY this phase and stop.
