# Project registry

**LucyOS (`Hetlife/lucyos-`, this repo) is the operating system, not a
project.** It is the one control layer — state, routing, approvals, budget —
that every project below runs under. It has no row here; it is where this
file lives.

A *project* is a separate repository LucyOS operates on — one business, one
codebase. Adding a new one means adding one row here and one folder next to
this file. Nothing else in the architecture needs to change.

| Project | Repo | Branch | Role | Status |
|---|---|---|---|---|
| **SEVAA Sales OS** | `het-life/sevaaconnect-realestate` | `main` | First revenue module — B2B sales system for SevaaConnect Solutions | EXP-001 (paid ₹2,499 consultation, warm network) designed and planned — `aion path` shows the 8 steps; T100 deliberately gated behind EXP-001 SUCCESS |

Folder for each project's plan, task queue and state:
```
PROJECTS/
  REGISTRY.md              <- this file
  sevaa-sales-os/          <- SEVAA project folder
    AION_TASK_QUEUE.md
    MACHINE_HANDOFF.json
    money_path.json        <- the ordered real-world steps to money (aion path)
    experiments/           <- one folder per experiment (aion experiments)
    bundles/
```

## Adding a new project

1. Add a row above: repo URL, branch, its one-sentence role, current status.
2. Create `PROJECTS/<name>/` with the same shape as `sevaa-sales-os/`: a task
   queue, a `MACHINE_HANDOFF.json`, and (if the repo needs code landed by an
   agent without push access) a `bundles/` folder.
3. If the project needs its own integration contract with AION (webhooks,
   approvals, revenue rows), copy the pattern in `aion_core/sevaa.py` — signed
   inbound events, an explicit allow-list of fields that may cross the
   boundary, and a forbidden-key test against real serialized bytes.
4. Register the machine, if a new one is involved, the same way Mark-2 is
   documented in `docs/SERVER_DEPLOYMENT.md`.

Never invent a project folder for a repo not listed above — every project's
existence should be traceable to an actual owner decision, not assumed.
