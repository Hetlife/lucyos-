# 13 — Current reality after the merge phase (2026-09-30, second pass)

Baseline moved: `origin/main` = `fad9ed4` (#73 context compiler and #88 docs merged after the first pass). Everything below was re-measured on that tree merged into the planning branch.

| Fact | Value | How measured |
|---|---|---|
| Tests | **810 OK, 2 skipped**, 148 s (was 795) | local full run |
| CI on `fad9ed4` | run #383 success; run #382 (#73's merge SHA `09fad0a`) **cancelled** again by the next push | Actions |
| Gates | portability 0 violations; `aion scan .` clean; anti-dup ok; boundary ratchet 2 warnings (unchanged) | local |
| Authority drift | **6 files** (worker.py joined the list after #73) | `verify_authority.py self` |
| Branches | 127 remote: 54 CONTAINED, 7 PATCH_IN_BASE, 7 UNRELATED, 59 UNIQUE (3 of them are Fable's) | `scripts/branch_ledger.py` -> `evidence/branch_ledger_20260930b.tsv` |
| Open PRs | #2, #53, #62 (all decided in `03_`: close) | GitHub |
| Remote branch deletion from an agent session | still refused (push --delete hangs up); `fable/FABLE-10-override-20260930` is redundant now that #73 carried the override and was deleted locally only | attempted |
| Context compiler | on every `worker` execution, before RUNNING, for every class including DET; build 76 ms, cache hit 43 ms, 27 sources, 12 KB markdown; fail-closed | measured with a seeded temp home |
| Dead-by-import modules | `guardian.py`, `tempworker.py`, `intake.py`, `sync_outbox.py` have no importer outside their tests (contracts C5/C6/C3/C2 skeletons) | grep |
| Live hosts | still unobserved (Lucy-den, Mark-2, pad). Nothing in this pass changes that; TR-0-04 remains the first Codex task | — |

## Subsystem classification (delta from `02_`; unchanged rows omitted)
| Subsystem | Now | Note |
|---|---|---|
| Context compiler / memory | CI_VERIFIED (was PARTIAL) | merged; worker-integrated; owner flag `context_compiler_enabled` |
| Worker execution | CI_VERIFIED but **coupled**: DET commands now require a successful repo context compile | ISSUE-030 |
| Authority freeze | DEGRADED (6 drifts, incl. two constitutional-class files) | TR-0-03 more urgent |
| Deployment guardian, temp workers, intake, sync outbox | DESIGNED, unreachable at runtime | cleanup register C-05 |
| RDC | ABSENT in repo (no reference anywhere) | owner tooling only; out of scope |
| Framer | ABSENT in repo; only Drive design docs (`LUCYOS_UI_UX_MASTER_REFERENCE`, 2026-09-17) | interface plan reuses `web/` |

## What the merge phase closed
Context compiler (#73), docs corrections (#88), the R-/C-/M- runnability stack (#75–#87). Nothing else was waiting on a merge; the remaining unique branches are salvage or reject per `03_`.
