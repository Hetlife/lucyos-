# S-46 Context Pilot Results

**State:** measured on ratified integration `7a657ff`; no estimates are
presented as observations.

## Pilot evidence

| Pilot | Context proxy files | Source LOC | Governance LOC | Approx. tokens | Touched files | Tests / wall time | Actual opened files / calls / attempts |
|---|---:|---:|---:|---:|---:|---|---|
| S-47 `aion verify` | 102 | 15,212 | 1,240 | 188,037.5 | 3 | 615 / 57.332 s | not recorded; not inferred |
| S-49 hermetic tests | 63 | 6,881 | 1,240 | 95,585.5 | 2 | 615 / 57.332 s | not recorded; not inferred |

The proxy came from `scripts/task_context_profiler.py` using the actual
touched files plus one import hop. It is reproducible context measurement, not
a claim about model tokens or files physically opened.

## Measured comparison

- Baseline full suite: 562 tests / 46.1 s.
- S-47/S-49 integration: 615 tests / 57.332 s (+53 tests, +24.4%).
- With S-48 tests: 618 tests / 57.730 s (+56 tests, +25.2%). The +10% runtime
  target is **not met** and remains follow-up work.
- Complexity snapshot: 71 modules, 13,584 LOC, 11 DFS cycles, one function
  over 120 lines. Earlier baseline was 67 modules / 14 cycles; cycles improved,
  but additive work means no overall LOC reduction is claimed.
- Duplication scan: zero duplicate function bodies.
- Operations: deep health healthy, zero tasks/errors, backup present, secret
  mode 0600, 9/9 skills enabled; `aion verify --json` READY.

## Context target and exclusions

The context proxies are 102 and 63 files, above the ≤10 target. The profiler
includes the fixed governance corpus and test imports, so the target is not
demonstrated. No worker packet recorded an excluded-file request; no manifest
fix is claimed.

## Verdict

**PASS with explicit follow-ups:** both pilots landed and are verified, while
context-size and runtime targets are not met/measurable with available worker
telemetry. S-46 authorizes no CI or production change.

Separate S-48 debt: two pre-existing SQLite boundary findings are assessed
separately and are not fixed by S-46.
