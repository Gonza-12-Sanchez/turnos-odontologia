---
description: "Recommend skills for this stack only (find-skill, recommend-only, no auto-install)"
---

Use the `skill` tool to invoke the `active-orchestrator` skill with the standalone find-skill entrypoint (`find-skill`).

It dispatches `find-skill` in RECOMMEND-ONLY mode: derive stack/domains/problem from `.active-orchestrator-state.json`, return the recommendations table, and let the USER pick what to install (multi-select, none is valid). Never install anything autonomously. Run ONLY this phase and stop.
