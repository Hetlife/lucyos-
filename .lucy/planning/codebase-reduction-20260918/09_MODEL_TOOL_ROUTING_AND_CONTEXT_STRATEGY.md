# 09/10 — Model & Tool Routing, Context & Token Strategy

## 1. Routing — reuse `agents.route`, do not invent a second ladder

The kernel already routes by `kind`, `complexity`, `stakes`, `ambiguity` onto `ORDER = [DET, A, B, C, D]`
(`aion route <kind> --complexity N --stakes S --ambiguity A`). This program uses the same ladder and the
same kinds; the table below is the *policy* the controller applies when it fills a task card's `EXECUTOR`.

| Work | Class | Who, in this program | Rule |
|---|---|---|---|
| repo scans, tests, diffs, import graph, LOC, hashing, secret scan, portability, authority verifier, context selection when deterministic | DET | `scripts/*`, `git`, `python3 -m unittest`, `./aion scan/context/route/architecture-check` | always first; its output is evidence |
| classify files/symbols, summarise already-selected files, label logs, cluster duplicate docs, propose search terms, draft docstrings/test scaffolds | A | local models on Lucy-den (Ollama; 3 models on Mark-2 per Drive baseline) | inside a worker's task only; output reviewed before commit; never decides |
| bounded coding, focused debugging, tests, scoped refactors | B | Codex CLI (`scripts/aion_codex_worker.sh` semantics: `-s workspace-write --ephemeral`), Claude Code | the executor for every L2 task |
| independent review of a B change | B (different session/vendor) or C | Claude Code ↔ Codex; `code-review` skill; CI | mandatory for L2+; author ≠ verifier |
| architecture, contradictory evidence, persistence, security, authority, cross-node design, 3rd-attempt failures, milestone reviews | C | Fable (this role), Opus-class | only at gates and escalations; never for tedium |
| approvals, money, credentials, deploy, deletion | D | owner | 04 §5 |

Escalation is one rung at a time (`agents.escalate`), never straight to the owner; a task that reaches C
twice for the same reason becomes a Fable card, not a fourth attempt.

**Cost discipline metrics** come from the existing `model_usage` table (`metrics.record_usage`;
`aion routing-report`; `aion usage` to record). Workers that can report tokens do so per task with
`--task-id`; where a CLI cannot report tokens, the deterministic proxy (files/LOC read) from S-43 is used.

## 2. Context strategy — extend `aion context`, salvage `context_pack.py`, no third system

What exists:
- `aion_core/context.py` (`aion context <TASK_ID>`): work order from the AION task row — objective, why,
  project, status/priority/value, router suggestion, resume `current_state`/bottleneck, `output_location`
  as FILES, success criteria, validation method, constraints, related memory (FTS), recent errors, the
  7-field result-packet contract; `security.redact` on output. **Blind to the repository.**
- `feature/context-pack:aion_core/context_pack.py`: repo-delta packet since
  `meta.last_high_model_reviewed_commit`, dirty status, health, enabled skills, recommended files with
  sha256, 30 KiB markdown cap, `mark_reviewed()`. **Blind to the task.** Stale base.
- Module manifests: do not exist yet (S-44).

Decision (S-45): one extension of `context.py`, behind new optional args, preserving today's output
byte-for-byte when the args are absent:

```
aion context <TASK_ID> [--module <name>] [--budget-bytes N] [--since <sha>] [--json]
```
adds sections, in this order, after `## FILES`:
```
## MODULE <name>            purpose, public seam, invariants, risk, ADR pointers (from the manifest)
## OWNED FILES              path (bytes, sha256[:12]) — capped by budget; tests listed separately
## TESTS                    the manifest's tests + any test importing an owned module
## NEIGHBOURS               allowed_dependencies (1 hop) — names only, never contents
## DELTA SINCE <sha>        changed owned files since --since or meta.last_high_model_reviewed_commit
## EXCLUDED                 explicit: .lucy/planning/**, .lucy/archive/**, directives/**, docs/internal/**,
                            other modules' files, business/** for kernel tasks
## CANONICAL                origin/main sha, branch, dirty count
## ROLLBACK / COMMANDS      exact test + gate commands for this module
```
Budget: default 10 files / 200 KiB of listed source; exceeding it lists paths without content and says so.
A pack never inlines file contents beyond the budget — workers open files from the list.

Not built: a cache layer (packs are cheap and commit-aware; `git` is the cache), a "Context Pack Manager"
API, a JSON-with-embedded-source format (workers have the checkout). `context_pack.py`'s watermark and
sha listing are ported into `context.py`; the branch is then closed, not merged.

## 3. Standard context packet for a bounded coding task (what a worker receives)

1. canonical SHA and task branch name
2. the task card (08) — objective, success criteria, allowed/forbidden files, tests, stop conditions
3. `aion context <ID> --module <m>` output (≤ 10 files listed, ≤ 200 KiB)
4. the diff of the last attempt, if REWORK
5. the exact commands: targeted tests, full suite, gates, rollback

Nothing else. Not `START_HERE.md`, not the authority corpus (the card already encodes the constraints that
apply), not the planning folder. If the worker needs more, it says so in `BLOCKERS`; three such requests
for the same module means the manifest is wrong (07 M3 stop rule).

## 4. Pilot targets and how the controller measures context efficiency

Targets (DEV plan; targets, not guarantees): ≤ 10 relevant source files for ordinary bounded tasks;
≤ 25% of the S-43 baseline source-context volume; no full-repo read unless the card says architecture-wide.

Measurement per task (recorded in the checkpoint block and `14`):
- `files_listed` / `files_opened` (worker packet `ACTIONS` must list opened files; verifier spot-checks)
- `source_loc_listed`, `docs_loc_listed` (from the pack)
- `prompt_tokens`, `completion_tokens` where the CLI reports them (`aion usage` → `model_usage`)
- `calls`, `retries`, `attempts`, `wall_seconds`
- `first_try_green` (targeted tests pass on the first packet), `rework_count`
- baseline comparison: S-43 computes, for the same task *type*, the files/LOC an agent would read using
  the reference commits' touched sets plus one import hop.

## 5. Keeping the text corpus out of context (the largest lever)

Measured: governance/planning/skills/docs ≈ 15.6k lines vs 10k kernel. Rules from M3 onward:
- Packs exclude `.lucy/planning/**`, `.lucy/archive/**`, `directives/**`, `docs/internal/**`,
  `.lucy/handoffs/**` unless the task names a file.
- The authority constraints a worker must obey are carried as **card fields**, not as "read these six files".
- `START_HERE.md` becomes ≤ 60 lines and points to `aion context` first (S-54).
- Skill manifests (104) are inventory; a pack includes a manifest only if the task is a skill task.

## 6. Anti-bloat budgets (warnings first; gates only after measured false-positive rates)

| Budget | Threshold | Where measured | Becomes a gate when |
|---|---|---|---|
| function length | warn > 120 lines (today: 1 function, `cli._main` 564) | S-41 | M6 move #1 done |
| file length | warn > 700 lines (today: 0; `fable.py` 678) | S-41 | M6 |
| module fan-out | warn > 20 imports (today: `cli` 41) | S-41 | M6 |
| new import cycle | warn on any cycle not in the S-41 baseline list | S-48 | M4 exit |
| context pack size | hard: 10 files / 200 KiB listed | S-45 | immediately (it is a budget, not a gate) |
| duplicate function bodies | warn on AST-hash duplicates > 15 lines | S-42 | M5 |
| stale docs | warn on any `.md` referencing a missing path | S-42 | M5 |
| generated/runtime content in git | already gated (`.gitignore`, `aion scan`) | CI | — |
| manifest freshness | warn if any tracked `.py` is unowned | S-44 test | M2 exit (test is the gate) |
| ADR for new core mechanism | anti-dup already fails new `aion_core` modules not in the baseline | CI | — |
