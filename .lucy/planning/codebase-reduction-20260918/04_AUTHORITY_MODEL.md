# 04/15 — Authority Model, Autonomy Levels, Owner Approval Matrix

Extends, never replaces: `.lucy/handoffs/2026-09-16/03_HIGH_TO_LOW_MODEL_AUTHORITY_CONTRACT.md`,
`.lucy/authority/HIGH_MODEL_BASELINE.json` (`allowed_executor_scope`, `escalation_rules`,
`owner_only_actions`), `PROTECTED_PATHS.md`, contracts C5/C6. Where this file and the baseline differ, the
baseline wins until the owner merges the baseline change proposed in OWNER-08.

## 1. Hierarchy — as proposed, and as corrected by repository evidence

Proposed: `OWNER → FABLE → CHATGPT/DEV → LUCY-ARCHITECT-AUDIT → CODEX/CLAUDE/LOCAL → VERIFIER`.

Correction 1 — **Lucy-architect-audit is a gate, not a layer.** In the repo it is not an agent; it is the
composition of (a) `scripts/verify_authority.py strict` (protected paths need a declared task ID and override),
(b) `verify_authority.py anti-dup` (diff-based: new `aion_core` module, `sqlite3.connect`, `CREATE TABLE`,
unit files, orchestration imports, governor/scheduler-named files), (c) `scripts/check_portability.py` (C1
ratchet), (d) `./aion scan` (secrets), (e) `./aion architecture-check <proposal.json>` (skill-integration
checklist), and (f) a **high-model review** (Fable, or Opus-class) for everything the tools cannot judge:
semantics, duplication of *behaviour*, boundary intent. A layer in a chain of command can be talked past; a
gate composed of deterministic checks cannot. So the audit sits *between* every worker and every merge, and is
owned by Fable (rules) and executed by tools (checks).

Correction 2 — **Verifier is a role, not a person.** Independence is the property: for any L2+ change the
verifier is a different session/vendor from the author (Codex ↔ Claude Code), plus CI from a fresh checkout,
plus Fable for L3+. The 2026-09-16 contract already reserves OPUS as "adversarial review; proposes, never
merges" — the verifier role inherits that scope.

Correction 3 — **The controller is new.** No `allowed_executor_scope` entry exists for a ChatGPT/DEV
controller. Until OWNER-08 lands the baseline change, the controller operates under the `SONNET` scope
(strict subset: one task per branch, allowed paths only, never merge to canonical) **plus** the dispatch and
checkpoint duties below.

Resulting chain:

```
OWNER ────────────── L4/L5 decisions; merges to main; protection; deploy; money; credentials
  │
FABLE ────────────── architecture, sequencing, task graph, gates, baseline/protected paths (lands via owner PR)
  │
CONTROLLER (ChatGPT/DEV) ── sync, select READY task, build evidence pack, classify level, dispatch, verify
  │                          independence, checkpoint, escalate at boundaries; merges only into research branch
  ├─ GATE: Lucy-architect-audit = deterministic checks + high-model review (before AND after each change)
  │
WORKERS ─────────── Codex (bounded coding, Lucy-den), Claude Code (bounded coding/review), local models
  │                  (classify/summarise/draft), deterministic tools (measure/test/diff/scan)
  │
VERIFIER ────────── the other worker + CI + (L3+) Fable; author ≠ verifier ≠ approver
```

## 2. Autonomy levels (refined from master prompt §7) mapped to existing machinery

| Level | Definition | Examples in this program | Required gates | Who may execute | May merge where | Existing mapping |
|---|---|---|---|---|---|---|
| **L0 READ-ONLY / MEASURE** | No repo write except under `evidence/` reports | `git`/AST scans, test runs, metrics, Drive reads | none | controller, any worker, local model | research branch (reports only) | C5 GREEN; `tasks` kind `count/diff/test_run` → DET |
| **L1 REVERSIBLE DOCS / METADATA** | Docs, manifests, schemas, reports, planning; no runtime path | module manifests, `evidence/*.md`, `CHECKPOINT.md`, task graph updates | secret scan | controller, workers | research branch, direct commit | C5 GREEN |
| **L2 BOUNDED REVERSIBLE CODE** | New/changed code outside protected paths, ≤ ~5 files, tests included, rollback = revert | `scripts/complexity_map.py`, `check_boundaries.py` (warn mode), `context.py` extension, salvaging tests | strict + anti-dup + portability + scan + targeted & full tests + **independent verifier** + architecture re-check | Codex/Claude, dispatched by controller | PR → research branch (controller merges after verification) **or** PR → `main` (owner merges) when the change must reach canonical | C5 GREEN/AMBER; `SONNET` scope |
| **L3 STRUCTURAL** | File moves, dependency rule *enforcement* (required CI), protected-but-overridable paths (`worker.py`, `db.py` migrations, `cli.py` dispatcher split), new `aion_core` module | M6 decomposition, boundary gate promotion, `resource-governor` salvage (S-03/S-04) | L2 gates + Fable plan + pilot evidence + task override in baseline + rollback branch/tag | Codex/Claude with Fable card | PR → `main`, **owner merges** | C5 AMBER; `task_overrides` |
| **L4 RUNTIME / CANONICAL AUTHORITY** | Mark-2 deploy, canonical state ownership, scheduler authority, network/credential/firewall, `systemd/**`, `deploy/**`, CI workflow, verifier, `.lucy/authority/**` | naming DC-1, enabling `enforce_admission`, controller scope in baseline | owner approval **before execution**; `verify_authority.py deploy`; deployment contract | Codex-on-Mark-2 (deploy only), Fable (docs) | owner admin-bypass merge | C5 RED; constitutional paths |
| **L5 IRREVERSIBLE / FINANCIAL / DESTRUCTIVE** | deletion of branches/tags/data, repo split, paid services, money, trading, credential rotation | branch cleanup (OWNER-03), any spend | owner only | owner | — | `owner_only_actions`; C8/C9 |

Rules that hold at every level:
- A worker may not author, verify and approve the same L2+ change.
- Crossing a level mid-task (e.g. an L2 fix needs `db.py`) means **stop, adopt the higher level, escalate**;
  never widen scope silently (baseline `escalation_rules[0]`).
- L2 merges into the research branch are allowed only when the research branch is never deployed
  (`MARK2_DEPLOYMENT_CONTRACT.md` §0 already guarantees this: only a SHA written in the contract deploys).

## 3. The architecture-audit gate, made executable

Pre-code (before any L2+ edit):
```
python3 scripts/verify_authority.py strict  --base origin/main --branch "$(git branch --show-current)"   # on the empty task branch: proves task-id detection works
python3 scripts/verify_authority.py anti-dup --base origin/main
./aion architecture-check <proposal.json>     # only when the task adds/changes a skill integration; otherwise the checklist below
```
High-model pre-code checklist (recorded in the task card's `ARCHITECTURE_AUDIT` field; Fable or verifier
answers, not the author): reuses existing seam? no second queue/state/scheduler/approval/memory/secret store/
plugin registry/governance layer? touches a protected path (→ level up)? changes a public seam used by
>1 module (→ L3)? rollback is a single revert? tests define the behaviour?

Post-change (before merge): the same commands on the final diff, plus `python3 scripts/check_portability.py`,
`./aion scan .`, full suite, and — once S-48 exists — `python3 scripts/check_boundaries.py`.

If any deterministic check BLOCKS or the high-model reviewer says NEEDS_REVIEW: the change does not merge.
No `continue-on-error`, no editing the verifier/baseline/workflow to pass (baseline `escalation_rules[1]`).

## 4. Role scopes (to be added to `allowed_executor_scope` by OWNER-08; binding as policy now)

- **CONTROLLER (ChatGPT/DEV):** read everything; write L0/L1 directly to the research branch; open task
  branches/PRs for L2 via workers; merge verified L2 into the research branch; never edit protected paths;
  never merge to `main`; never deploy; never spend; never create credentials; may invoke Lucy skills and
  `/learnrepo`; must checkpoint after every task; must stop at every gate in §5.
- **CODEX (Lucy-den):** L2 implementation inside a task card's `FILES_ALLOWED`; runs tests; returns the
  7-field result packet (`STATUS / ACTIONS / FILES_CHANGED / TESTS / RESULTS / BLOCKERS / NEXT_ACTION`);
  never commits to `main`; never touches protected paths without an override; `-s workspace-write --ephemeral`.
- **CODEX (Mark-2):** deploy only; unchanged from the deployment contract.
- **CLAUDE CODE:** L2 implementation or independent verification (never both for the same change);
  review reports; may run `/learnrepo`, `smallest-fix`, `code-review`.
- **LOCAL MODELS (class A):** classify/summarise/cluster/draft *inside* a worker's task; output is never
  committed without a worker's review; no architecture, security, persistence or authority decisions.
- **DETERMINISTIC TOOLS:** preferred for everything repeatable; their output is evidence, a model's claim is not.
- **FABLE:** L3 plans, gate reviews, escalations, milestone reviews, baseline/protected-path proposals.
- **OWNER:** §5.

## 5. Owner approval matrix

| Action | Level | When asked | Artifact the owner reads | Default if unanswered |
|---|---|---|---|---|
| Ratify this package and the 8-module direction | — | M2 gate | 00, 02, S-44 manifests | controller continues M0–M2 (L0/L1) only |
| OWNER-06 node checkout policy: name DC-1 = `66e3a4e` (or successor) **or** keep `2cd3cc5` and prioritise S-03/S-04 | L4 | M0 | `evidence/M0_BASELINE.md` | nodes untouched; measurements continue on `main` worktrees |
| OWNER-07 confirm branch protection state / enable (OWNER-01 carry-over) | L4 | M0 | GitHub settings | controller treats `main` as unprotected: never pushes to it |
| OWNER-08 merge the baseline change adding `CONTROLLER` scope + `S-40…S-59` overrides where needed | L4 (constitutional) | after M1 | Fable PR (authority-gate fails by design) | controller stays inside `SONNET` scope |
| Merge any L2 PR that targets `main` (e.g. S-45 `context.py`, S-47 salvage) | L3 promotion | per PR | PR body (evidence, tests, verifier report) | work continues on research branch; PR waits |
| Promote `check_boundaries.py` to a required CI step | L4 | M4 exit | false-positive log | stays warning-only |
| Archive/prune governance text corpus | L1 but owner-visible | M5 | S-42 stale-doc report | nothing archived |
| M6 file moves / `cli.py` dispatcher split | L3 | M6 | Fable plan + pilot metrics | not started |
| M7 topology decision | L4 | M7 | 02 + M3/M4/M6 metrics | remains A |
| Branch/tag deletions (OWNER-03 carry-over) | L5 | after M5 | verified-contained list | nothing deleted |
| Any Mark-2 deploy, `enforce_admission`, credentials, spend, trading | L4/L5 | never by this program | deployment contract | refused |

Interrupt budget: outside this table the controller does **not** ask the owner. Everything L0–L2 proceeds.
