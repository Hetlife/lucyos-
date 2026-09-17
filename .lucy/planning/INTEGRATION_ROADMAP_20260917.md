# LucyOS / Mark-2 — Integration & Autonomy Roadmap (planning skeleton)

- **Status**: DRAFT SKELETON, awaiting external review. Not approved. Not executed.
- **Author**: Opus planning pass, 2026-09-17.
- **Base of record**: `integration/consolidation-20260916` @ `c11fcb6`.
- **Purpose**: move Mark-2 from a 23-open-PR state to a healthy canonical branch
  and one reliable autonomous loop, without weakening any gate.
- **Reviewer**: read Part 4 for your exact task and output contract.

Nothing in this file authorises a merge, a deploy, a spend, or a governance
change. It is a plan to be reviewed.

---

## PART 0 — GROUND TRUTH (verified against the repo; do not re-derive)

- `integration/consolidation-20260916` @ `c11fcb6`, 35 commits ahead of `main`,
  0 behind. Nothing merged yet.
- 23 task PRs (#13–#35). **Every one branches from that same commit `c11fcb6`.**
- CI: **16 green** — #13, 14, 15, 16, 17, 18, 19, 21, 22, 23, 26, 27, 28, 29, 30, 32.
- CI: **7 failing**, two distinct causes:
  - **5 fail the authority gate only, tests green**: #20 (S-22), #24 (S-23),
    #25 (S-17), #33 (S-29), #35 (S-16). Cause: `HIGH_MODEL_BASELINE.json` is
    missing five `aion_core_modules` entries (`portability`, `guardian`,
    `experiments`, `money_path`, `tempworker`) and one `task_overrides` entry
    (`S-22`). This is **one omission, not five decisions**.
  - **2 substantive findings**: #31 (S-20) proves `PROTECTED_PATHS.md` omits the
    `.lucy/authority/` prefix on one path. #34 (S-02) trips
    `check_portability.py` on the literal `"systemd "` inside `worker.py`'s
    `FORBIDDEN` security denylist — a false positive the rule cannot
    distinguish from a real call.
- **Merge-conflict surface** (this is what orders the waves):
  `cli.py` touched by 6 PRs · `db.py` by 3 · `bridges/drive_bridge.py` by 3 ·
  `reports.py` by 2 · `health.py` by 2. Conflicts are additive and mechanical,
  but they are certain, not hypothetical.
- `macos-readiness` is `continue-on-error: true` and is **already green on #14
  (S-19)**, so merge order changes its colour. It is a lever, not a defect.
- `authority-drift` fails by design; the freeze SHA legitimately lags between
  merges and re-freezes.
- S-16 was absent from the queue's own READY index despite carrying
  `STATUS: READY`, which is why it was originally missed.

### Existing seams that MUST be reused, never rebuilt
`AGENTS/{work_orders,results,prompts}` · `scripts/aion_codex_worker.sh`
(already mandates the seven-field result packet) · `worker.py` (singleton
execution lock, `_validate` evidence gate, DET → Ollama → cloud routing,
work-order preservation when an executor is unavailable) · `errors.py`
(`record`/`resolve`/`classify`/`repeated`) · `resume.py`
(`checkpoint`/`boot`/`bottleneck`) · `learnrepo.py` (lease + stale-lease
recovery) · `verify_authority.py` (`strict`/`anti-dup`/`self`/`freeze`).

### Canonical task columns (verified in `db.py`)
`tasks` already carries `success_criteria`, `validation_method`,
`output_location`, `exec_command`, `validation_command`, `evidence`,
`next_action`, `last_error`, `model_class`, `dependencies`, `blockers`.
**Any work-order or result contract binds to these columns.** A parallel store
would be rejected by anti-dup and is forbidden.

---

## PART 1 — TARGET ARCHITECTURE

One loop, entered only through `build_loop.sh` under `aion-work.timer`.

Owner objectives and approvals land in the canonical shared brain. AION
governance and the planner decompose them into queue tasks carrying an explicit
`model_class`. `worker.py` holds the sole execution lock and routes **DET first**
(`exec_command`), **Ollama second** (class A), **bounded Codex third** (class B
via `cloud_command`). Every completion passes the evidence gate before
`tasks.complete`. Failures become `errors` rows; unexpected findings become
append-only notes the planner reads. `resume.boot()` re-derives the bottleneck on
every restart, so the loop is stateless between runs and never trusts memory over
the database.

Opus is used only for architecture, governance-sensitive planning, and reviewing
unexpected failures. Codex does bounded implementation, testing, debugging and
maintenance from work orders that carry their own context, so it never needs to
rediscover the repository.

---

## PART 2 — INTEGRATION ROADMAP

Ordered by file-overlap risk, lowest first. Full suite plus both authority gates
between waves. **Two PRs touching the same file never share a wave.**

| Wave | Who | Contents | Note |
|---|---|---|---|
| 0 | **OWNER** | Governance commit: five module names + `S-22` override + `PROTECTED_PATHS.md` prefix fix; plus the `check_portability.py` decision | Blocking. Unblocks six PRs |
| 1 | autonomous | #23, #22, #13, #32, #31, #15, #25, #16, #19 | Zero file overlap |
| 2 | autonomous | #28, #26, #20 | Single-file owners |
| 3 | sequential | #17 → #18 → #35 | All extend `db.py` `_ADDED_COLUMNS`; re-run `upgrade-from-main-schema` after each |
| 4 | sequential | #14 → #21 | #14 first: it turns `macos-readiness` green for everything after |
| 5 | sequential | #27 → #29 → #30 → #24 → #33 | The six-way `cli.py` convergence; resolve additively, full suite between each |
| 6 | reviewed | #34 | Largest surface; changes the argv execution boundary in `worker.py` |
| 7 | **OWNER** | `verify_authority.py freeze`, full CI on integration, merge integration → main | |
| 8 | autonomous | S-11, S-12 (need S-10 landed) · S-25 (needs S-05) · S-03 → S-04 (need S-02) | Newly unblocked dependents |

For Wave 0's `check_portability.py` decision: **preferred** is refining the rule
so string-literal denylists stop matching; **alternative** is a
`KNOWN_EXCEPTIONS` entry owned by S-02. The rule refinement prevents the same
false positive recurring on every future denylist entry.

Waves 1–6 and 8 are mechanically autonomous once Wave 0 lands.

---

## PART 3 — CODEX EXECUTION MODEL, FEEDBACK LOOP, LOOP V2

### 3.1 Codex execution model
One work order per task at `AGENTS/work_orders/<TASK_ID>.md`, generated by
`aion context <TASK_ID>`, carrying objective, allowed and forbidden paths,
acceptance criteria, exact validation commands, and base SHA. **Codex never
receives the repository as context and never receives the queue.**

`scripts/aion_codex_worker.sh` already carries the standing preamble and the
seven-field result-packet contract (`STATUS` / `ACTIONS` / `FILES_CHANGED` /
`TESTS` / `RESULTS` / `BLOCKERS` / `NEXT_ACTION`). Keep both as the single
boundary. Codex writes its packet to `AGENTS/results/<TASK_ID>.md`. `worker.py`
parses it, runs the task's own `validation_command`, and only then permits
`tasks.complete`. **A packet claiming success without passing validation is a
failure, not a completion.**

Resume is already solved and must not be reinvented: work orders persist when an
executor is unavailable, the singleton lock prevents double execution, and
`resume.boot()` rebuilds position from the database.

### 3.2 Feedback / error loop
- `errors` table via `errors.record()` stays the canonical machine-readable
  failure log. `errors.repeated()` is the existing escalation trigger.
- **One new append-only file**: `.lucy/execution/CODEX_FINDINGS.md`. Codex may
  append a dated entry (task ID, expected, observed, evidence path) and may do
  nothing else to it. It is the **only** governance-adjacent file Codex can write.
- The planner reads findings plus open errors, decides whether instructions are
  actually wrong, and is the only actor that may edit
  `AGENTS/prompts/MASTER_CURRENT.md` or anything under `.lucy/authority/`.
- `resume.boot()` surfaces unreviewed findings in the bottleneck line so they
  cannot accumulate silently.

**Hard rule**: a finding is a request for review, never a licence to self-amend.
Codex must be structurally incapable of changing its own instructions.

### 3.3 Autonomous Loop V2 (design only; do not build in this pass)
Change `build_loop.sh` in place rather than adding a second loop. Add an
integration-health preflight that refuses to run on a red canonical branch. Wire
the Codex tier through the existing `cloud_command` seam with a bounded per-task
timeout. Make `errors.repeated()` pause and escalate instead of retrying. Feed
the new nightly evidence producers (history scan, runtime inventory, audit
export, encrypted backup, drive check, OpenClaw check) into health rather than
ad-hoc reports. Reuse the `learnrepo` lease pattern for any scheduling so no
second scheduler appears. Leave the evidence gate and singleton lock untouched.
The loop's improvement step is reading findings plus errors and proposing queue
tasks, never editing its own governance.

---

## PART 4 — REVIEWER TASK AND OUTPUT CONTRACT

You are cross-checking this skeleton and adding implementation detail so it can
become Codex-ready repo instructions. **You are not executing anything.** Make no
repository modifications.

### Rules that prevent the known failure modes — obey literally
1. **Never invent a repo fact.** If a detail is not in Part 0 or this document,
   mark it `ASSUMPTION` and state the exact command or file that would confirm
   it. An unmarked guess is the worst possible output.
2. **Never weaken, skip, disable or quarantine a test, gate or check** to make
   integration simpler or CI green. If a gate blocks a wave, the gate wins and
   the plan changes.
3. **Never propose a second loop, scheduler, or state store.** The anti-dup
   verifier mechanically rejects new top-level `aion_core` modules,
   `sqlite3.connect` outside the allowlist, `CREATE TABLE` outside `db.py`,
   and governor/scheduler-named files. Extend an existing seam.
4. **Codex must never edit its own governing instructions** (`AGENTS/prompts/**`,
   `.lucy/authority/**`). Append-only findings is its entire write surface there.
5. **Do not reorder waves** without justifying the change from the
   file-overlap map in Part 0. Two PRs touching one file never share a wave.
6. **Preserve**: singleton locking, evidence gates (an exit code is never proof),
   secret protections, restart/resume, authority boundaries, dependency rules,
   auditability.
7. No spending, no credential handling, no external accounts, no real capital,
   no deployment. Strategy Factory stays paper/sandbox only.
8. **Flag disagreement explicitly.** If this skeleton is wrong, say so and give
   the correction. Do not silently rewrite it.

### Produce exactly this, in order, compact, no source-code dumps
- **A. ERRORS FOUND** — anything wrong, unsafe, or internally inconsistent.
  Highest-value section. If genuinely none, say so plainly.
- **B. OMISSIONS** — what a competent integrator would need that is missing.
- **C. WAVE VALIDATION** — per wave: exact conflict risk and the exact
  validation commands to run between waves. Hardest attention on the six-way
  `cli.py` convergence (Wave 5) and the three-way `db.py` sequence (Wave 3).
- **D. WORK ORDER SPEC** — exact field list for
  `AGENTS/work_orders/<TASK_ID>.md` and the exact parse contract for
  `AGENTS/results/<TASK_ID>.md`, such that `worker.py` can mechanically reject a
  packet claiming success without passing validation. **Bind every field to the
  existing `tasks` columns listed in Part 0**: state which column supplies each
  work-order field and which column each result field is checked against.
- **E. FINDINGS FILE SPEC** — entry schema for
  `.lucy/execution/CODEX_FINDINGS.md` plus the guard keeping Codex out of every
  other governance path.
- **F. OPEN QUESTIONS FOR THE OWNER** — genuine decisions only, not tasks.

Be concise and dense. Prefer a table or short list over prose. Do not restate
this skeleton back.

---

## PART 5 — APPROVAL POINTS (owner only)

1. The Wave 0 governance commit (baseline allowlist, `S-22` override,
   protected-paths doc fix).
2. The `check_portability.py` rule decision for S-02.
3. Merging integration into `main`, and the post-integration re-freeze SHA.
4. Enabling any unattended loop that can push; branch protection or
   required-check changes.
5. Turning on `resource_governor.enforce_admission`.
6. Any semantic change to authority, evidence gates, or executor scope.

Everything in Waves 1–6 and 8 proceeds without approval.
