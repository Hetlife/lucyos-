# Fable readiness — work log

Prepared cheaply (deterministic tools + this session) so a paid Fable session
starts with settled state instead of rediscovering it. Every line below comes
from a real command run against the shared brain, not from documentation.

## 2026-09-04 — measurement before any change

`aion fable-ready` on the local shared brain:

```
NOT YET FABLE READY
Environment READY · OpenClaw READY · Repository READY · Backup NOT READY
Shared Brain READY · Task Queue NOT READY · Checkpoint READY · Resume READY
Ollama NOT REQUIRED · Fable Context READY · Budget Governor READY · Security PASS
gaps: task_queue=NOT READY; no class-C task queued
```

Root causes, verified:

| Finding | Evidence | Fix class |
|---|---|---|
| Task table is empty, brain never seeded | `seeded_at: None`, `select count(*) from tasks` = 0 | deterministic: `aion seed` |
| Seed already contains the right Class-C jobs | `seed.py` TASKS: "Design the first real revenue experiment", "Decompose the revenue path into work orders", "Define the milestone ladder", "Adversarially review the bridge" | none needed |
| Seed also re-queues the phone interface as Class-C | that task is built, pushed (`b59a9df`) and verified live | mark DONE with evidence after seeding, so Fable is not handed finished work |
| Budget contradiction | governor + `build_budget_cap_inr` meta = **₹2,000** (matches directive) but `PHASES` sums to ₹1,000 + ₹3,000 = **₹4,000**, and `FABLE_BUDGET.json` tells Fable `maximum_cumulative_authorization: 4000` | code: phases must sum to ₹2,000; 5 test assertions pin 4000 |
| Latent bug | `set_phase()` writes `build_budget_cap_inr = BUDGET_CAP_INR`, so switching phase would silently raise the governor cap from 2,000 to 4,000 | fixed by the same constant change |
| No secret store, no backup yet | health: `secret_store` and `backup` failing | deterministic: `aion secrets init`, `aion backup` |
| Mission at zero, truthfully | `finance` rows = 0, M0 not reached, real revenue ₹0 | none — this is the correct reading |

## Decision — phase caps under the ₹2,000 hard ceiling

The directive's guideline split is A 35% architecture/decisions, B 20%
orchestration, C 15% debugging, D 15% adversarial/economic review, E 15%
reserve. The existing two-phase model maps onto it directly:

| Phase | Covers | Cap |
|---|---|---|
| 1 — offline planning (no machine) | A | ₹700 |
| 2 — on-machine execution | B + C + D + E | ₹1,300 |
| **cumulative hard ceiling** | | **₹2,000** |

Recommended first top-up is therefore ₹700, not ₹1,000. The reserve inside
phase 2 is not a spending target; the governor thresholds (25/50/70/85/95%)
already enforce the downshift.

Recorded here so it is not reopened without new evidence.

## Result — genuinely FABLE READY

Closed the three real gaps, all deterministic, no reasoning spent:

```
aion seed              -> 8 decisions + 9 opening tasks queued
aion secrets init      -> private_state/secrets.env created (0600)
aion backup            -> taken and restore-verified: integrity=ok, 9 tasks, 17 memories
```

Two of the nine seeded tasks turned out to already be real work, not new work —
marked DONE with evidence rather than left for Fable to redo:

- **Milestone ladder (M0-M6)**: already implemented in `aion_core/milestones.py`,
  computed strictly from `finance` rows with `stage=ACTUAL`. Verified by running
  `aion milestones` — correctly reports all six not-yet-reached against real
  (zero) revenue.
- **Phone interface**: already built and pushed (`b59a9df`), 25 tests passing,
  verified live with real HTTP round trips earlier this session.

Re-measured after trimming:

```
FABLE READY
Task Queue: READY · Backup: READY · Budget Governor: READY · Security: PASS
Queued strong-model work:
  TASK-1BB538FF  Design the first real revenue experiment end to end
  TASK-94945B7C  Adversarially review the bridge's external exposure
RECOMMENDED INITIAL CREDIT: INR 700
MAXIMUM CUMULATIVE AUTHORIZATION: INR 2000
```

This is the real bottleneck now: not infrastructure, a validated revenue
experiment. That is exactly the two-item queue a strong-reasoning session
should spend its first credit on.
