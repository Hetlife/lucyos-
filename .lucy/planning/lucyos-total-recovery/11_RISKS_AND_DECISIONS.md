# 11 — Risks and decisions

## Decisions taken by Fable (owner may overrule)
| ID | Decision | Why |
|---|---|---|
| D-1 | AION core is the kernel; no rewrite; no second control plane | 795 tests, CI on 4 platforms, restore- and resume-proven; every "replacement" branch duplicated it |
| D-2 | Company = workspace (namespace + policy); project = first-class; app = integration manifest | smallest model that isolates permissions/knowledge/secrets/models; reuses `project` column and skill manifests |
| D-3 | OpenClaw is the primary owner channel; direct Meta bridge stays optional/dormant | owner decision R-06; OpenClaw already carries WhatsApp; Meta path needs a public tunnel |
| D-6 | SCG COSE gateway rejected as implemented; design retained; device trust later via stdlib HMAC envelopes inside the OpenClaw path | third-party crypto deps and CI edits violate core invariants; `status.read` only today |
| D-7 | Reject `feature/resource-governor`, `feature/unlazy-completion`, `feature/taskcheck-mvp`, `feature/context-pack`, PR #2 | duplicates or vendored deps; nothing on the critical path needs them |
| D-9 | Mark-2 remains non-canonical forever; Mac mini becomes primary after L6; Lucy-den becomes dev/secondary | one truth; Mac is the intended always-on host |
| D-10 | `scripts/branch_ledger.py` replaces hand-made branch lists | root cause of the #88 misclassification |

## Decisions owed by the owner
| ID | Decision | Default if silent |
|---|---|---|
| D-4 | LucyNest pad: read-only status display, or secondary approval surface (paired TLS + explicit confirm)? | read-only until L2 is proven via OpenClaw |
| D-5 | Bridge unit `Restart=always/5s` -> `on-failure` with burst limit? | change it (TR-1-04) |
| D-8 | Retire `fable.py` launch pack + seeded mission tasks once this package is the handoff mechanism? | freeze now, remove in phase 5 |
| D-11 | Delete the 54 CONTAINED + 7 PATCH_IN_BASE branches after tagging? Close #2, #11, #53, #62? | tag now; delete on your word |
| D-12 | First value workflow: SEVAA reconcile/brief (needs token) or strategy-factory (needs project layer)? | SEVAA first (weeks), strategy-factory second (after phase 5) |
| D-13 | Tunnel provider for PWA/LucyNest (Tailscale Serve is free) | Tailscale |
| D-14 | Mac mini purchase timing relative to L2/L3 | after L3 |

## Risks
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Live hosts differ from repo assumptions | high | phases 1–3 mis-scoped | TR-0-04 census first |
| Authority drift keeps growing; drift signal ignored | high | protected files change unnoticed | TR-0-03 + re-freeze after every protected merge (Fable checklist) |
| Owner bandwidth (merges, secrets, decisions) is the bottleneck | high | plan stalls | `12_` batches owner actions; everything else parallel |
| Branch deletion loses salvage | low after tagging | — | tags before deletes |
| Project layer widens core edits (db, governor, worker) | medium | authority friction | overrides recorded in the baseline first (TR-5-01) |
| WhatsApp/OpenClaw identity weak (phone number as identity) | medium | unauthorised approval | envelope carries enrolled key id; approvals log principal; D-6 follow-up |
| Mac launchd semantics differ | medium | silent non-execution | TR-7-01 + reboot test |
| Cost creep from cloud executors | low | budget | governor caps per project (TR-5-06) |
