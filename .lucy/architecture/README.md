# Logical module contracts

These eight manifests implement S-44's M1-approved cut without moving files or
adding runtime behavior. Each JSON file in `modules/` follows `module.schema.json`.

| Module | Ownership |
| --- | --- |
| kernel.state | State/configuration utilities, bootstrap, backup and package metadata |
| kernel.tasks | Tasks, approvals, errors, recovery, sessions, packets and notebook |
| execution | Workers, agents, plans, governor, handoff, model/platform routing and host adapters |
| memory | Memory, recall, semantic index and task context |
| skills | Skills, learnrepo, architecture review, catalog and local skill resources |
| interfaces | Router, API, reports, CLI, bridges, web and OpenClaw integration |
| governance | Health, metrics, milestones, autonomy, guardian, portability, telemetry and scripts |
| business | Fable, experiments, money, deliveries, intake, outbox, seed and owner setup |

`owned_files` and other file lists use repository-relative `Path.glob` patterns;
`**` includes nested directories. Every pattern must match a file. Every tracked
Python file under `aion_core/`, `bridges/`, `scripts/` and `integrations/` must have
exactly one owner. Explicit core filenames keep new core modules from silently
acquiring an owner. Package metadata belongs to state; repository scripts belong
to governance, including the measurement scripts added during M1.

Dependencies name logical modules, exclude self-edges and describe observed
imports, not desired future layering. Allowed edges are aggregated from S-41's
[`dependency_graph.json`](../planning/codebase-reduction-20260918/evidence/dependency_graph.json)
using paths in its companion `complexity_map.json`. No allowed edge may lack
that evidence. The recorded graph predates S-42/S-43; ownership covers their
scripts too, without inventing additional dependency permissions. Empty forbidden
lists mean no separately ratified prohibition; they do not permit extra edges.

`public_api` identifies current seams (the approval entry point is `create`,
not the planning table's `request`). `state_touched` and `side_effects` describe
existing behavior. `tests` links executable evidence, `invariants` states module
constraints, and `protected_paths` lists owned files protected by the authority
baseline. Risk is low/medium/high; empty `adrs` means no standalone ADR is claimed.
The approved decision is recorded in the planning package's M1_GATE.md and §3
of 02_ARCHITECTURE_OPTIONS_AND_RECOMMENDED_DIRECTION.md.

Run `python3 -m unittest tests.test_module_manifests -v` for schema, file,
ownership, dependency evidence and negative-fixture checks. Update contracts and
evidence together when an approved task changes a boundary. These manifests do
not supersede authority rules; owner ratification remains the M2 exit gate.
