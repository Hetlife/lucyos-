# 14 — Metrics Scorecard

Baseline column = measured on `main` @ `66e3a4e` this pass unless marked (D) = owner's Drive baseline
(must reverify in S-40) or (S-43) = produced by that task. Targets are the DEV plan's pilot targets; a
target is never reported as met without the measurement command's output in `evidence/`.

## A. Repository / architecture

| Metric | Baseline | Command | Target / direction | Proves |
|---|---|---|---|---|
| tracked files | 386 | `git ls-files \| wc -l` | ↓ (no target; M5 measured) | M5 |
| Python files / LOC | 132 / 20,612 | `git ls-files '*.py' \| xargs wc -l` | stable ± (reduction is not the goal) | — |
| Markdown LOC / `.lucy`+`docs` LOC | 9,503 / 4,992+2,424 (D) | S-41 | **−25%** in `.lucy`+`docs` by M5 exit | M5, M9(3) |
| production modules | 67 | S-41 | 8 logical modules, 100% ownership | M2 |
| import-graph edges / density | S-41 | S-41 | ↓ after M6 move #1 | M6 |
| cycles | 14 (all via `resume↔tasks`, `learnrepo↔skills`) | S-41 | no new cycle (warn) → 0 new by M4 | M4 |
| max fan-out | `cli` 41 | S-41 | `cli` < 20 after M6 move #1 | M6 |
| functions > 120 lines | 1 (`cli._main` 564) | S-41 | 0 after M6 move #1 | M6 |
| files > 700 lines | 0 | S-41 | stays 0 | anti-bloat |
| duplicate function bodies (>15 lines) | S-42 | S-42 | each either merged or exception-listed | M5 |
| direct `sqlite3.connect` sites | 7 (all allow-listed) | grep | unchanged | boundary |
| stale doc references | S-42 | S-42 | 0 after M5 | M5 |
| unowned `.py` files | 100% unowned (no manifests) | S-44 test | 0 | M2 |

## B. Context / agent (per task; aggregated per task type)

| Metric | Baseline | Source | Target |
|---|---|---|---|
| files listed in pack | S-43 per type (reference commits' touched set + 1 import hop) | pack | ≤ 10 for bounded tasks |
| source LOC listed | S-43 | pack | ≤ 25% of S-43 baseline |
| docs/instruction LOC listed | S-43 (today: an agent following START_HERE reads ≥ 1,500 lines of governance) | pack | ≤ 200 |
| files actually opened | worker packet `ACTIONS` | verifier spot-check | ≤ listed + 2 |
| prompt / completion tokens | `model_usage` via `aion usage --task-id` where reported | `aion routing-report` | −50% vs baseline where measurable; otherwise "n/a", never estimated |
| calls per task | worker packet | — | ↓ |
| attempts / retries | checkpoint | — | mean ≤ 1.3 |
| first-try green | targeted tests on first packet | checkpoint | ≥ 80% (Executive Summary target, kept) |
| rework count | checkpoint | — | ≤ 1 per task |
| wall time per task | checkpoint | — | −25–50% for bounded tasks (DEV plan) |
| model class used | checkpoint | — | C only at gates/escalations |
| cost (INR) | `model_usage.cost_inr` | `aion money` | within governor caps; reported, not targeted |

Six representative task types and their reference commits for S-43 (real history, so the baseline is
measured, not estimated): small bug fix = `S-08` (`3131c9d`); new skill = `Q006` guard (`2b59aea`);
provider/adapter change = `S-10` host adapter (`612f5ef`); persistence change = `S-13` sync_outbox
(`1f28fd4`); cross-node task = `S-23` export/import (`08406e3`); project-specific = `S-29` experiments
(`6510ec9`).

## C. Test / CI

| Metric | Baseline | Target |
|---|---|---|
| full suite count / time | 562 / 46.1 s (52.5 s on Lucy-den (D)) | count never drops unexplained; time ≤ baseline +10% |
| targeted-test time per module | S-44 (module→tests map) | < 10 s for any single module |
| skipped tests | 2 (`ssh-keygen` absent) | explained skips only |
| CI conclusion on `main` | success (run 35279040189) | always; red = P0 |
| flaky tests | 0 known | 0; a flake is a bug |
| regression scope per task | full suite always | module-targeted first, full before merge (unchanged) |

## D. Operations (owner-reported until `aion verify` lands; never inferred)

| Metric | Baseline (D) | Target |
|---|---|---|
| Mark-2 health | healthy; integrity ok | unchanged by this program |
| Mark-2 queue | 0 ready / 0 running / 4 blocked-waiting / 13 done | not touched |
| node checkout vs `main` | `2cd3cc5` vs `66e3a4e` (136 behind) | 0 behind a contract-named SHA (OWNER-06) |
| duplicate processes / heartbeat freshness / idle use | unknown | reported by `aion verify` once salvaged (S-47) |
| cross-node failures | 0 known | 0 |

## E. Program health

| Metric | Target |
|---|---|
| `BLOCKED_TECHNICAL` tasks | 0 older than 7 days |
| `MERGE_CANDIDATE` PRs waiting on owner | ≤ 3, none older than 7 days (batched at gates) |
| owner interrupts per week | ≤ 1 outside gate reports |
| checkpoint freshness | every DONE/BLOCKED task has a block; no gap > 1 task |
| P4/P5 share after M9 | ≤ 20% of iterations |

## F. Reporting

`evidence/SCORECARD.md` is regenerated at every milestone gate from the commands above (S-41/S-43 emit
JSON; the controller renders the table). Drive receives the rendered file (22). Numbers without a command
and a SHA are not entered.
