# LucyOS / Mark-2 — Integration & Autonomy Roadmap **V2**

- **Status**: DRAFT SKELETON V2, planning only. Supersedes `INTEGRATION_ROADMAP_20260917.md` (kept for history).
- **Base of record**: `integration/consolidation-20260916` @ `c11fcb6`.
- **Ground truth**: Part 0 of the V1 roadmap, unchanged. Not restated here.
- Authorises no merge, deploy, spend, or governance change.

---

## 1. CORRECTIONS ACCEPTED / DISAGREEMENTS

All nine accepted. Two are **more severe** than the review stated; one is **already satisfied** and must be protected rather than built.

| # | Verdict | Repo evidence |
|---|---|---|
| 1 Result contract | **Accept, confirmed divergence** | `aion_codex_worker.sh` mandates 7 fields. `context.py:57-59` emits 11 with **different names**: `TASK_ID / STATUS / ACTIONS_TAKEN / FILES_CHANGED / TESTS_RUN / RESULTS / FAILURES / RISKS / ASSUMPTIONS / NEXT_RECOMMENDED_ACTION / EXACT_RESUME_POINT`. Not a superset: `ACTIONS_TAKEN` ≠ `ACTIONS`, `TESTS_RUN` ≠ `TESTS`. Any parser keyed to one silently fails the other. |
| 2 Parser does not exist | **Accept** | `worker.py` writes `AGENTS/work_orders/` (l.145, l.414) and never reads `AGENTS/results/`. V1 overstated this as built. |
| 3 Structural governance protection | **Accept** | `aion_codex_worker.sh` runs `codex exec -s workspace-write`. Prompt wording is not a write boundary. |
| 4 Bind to canonical task fields | **Accept** | Confirmed columns in `db.py`. Base SHA is envelope metadata only. |
| 5 Strict is task-scoped | **Accept, and worse than stated** | `verify_authority.py cmd_strict` hard-fails when `len(ids) != 1` (l.138-142), and `detect_task_ids` harvests every `Task-ID:` trailer in `mb..HEAD`. Running `strict` on an **accumulating** integration branch is not merely inadvisable, it is **guaranteed to fail as "ambiguous"** the moment a second override-using task lands. This breaks Waves 2, 3 and 6 as V1 described them. |
| 6 Wave 3 db validation | **Accept** | Three PRs extend `_ADDED_COLUMNS`; CI already has the `upgrade-from-main-schema` job to reuse. |
| 7 Wave 5 CLI convergence | **Accept, no reorder** | File-overlap evidence unchanged; no dependency evidence justifies reordering. |
| 8 Findings = evidence, not state | **Accept** | `errors` table remains canonical. |
| 9 Evidence semantics | **Accept — already satisfied, protect it** | `worker._validate` already reruns `validation_command` independently, falls back to `output_location` existence, and for class A/B without `exec_command` and without independent validation returns `needs_review: True` rather than DONE. **This is stronger than V1 claimed and must not be refactored away by the new parser.** |

**No disagreements.**

---

## 2. REVISED INTEGRATION WAVES

Ordering unchanged (no contrary file-overlap evidence). The **authority-gate usage is corrected throughout**.

### Gate protocol (replaces V1's aggregate assertion)
- **`strict`**: run **per candidate branch, before merge**, as `--base origin/integration/... --branch task/S-NN-...`. Never on the accumulated integration branch. Correction 5 makes this mandatory, not stylistic.
- **`anti-dup`**: run **cumulatively on the evolving integration branch** after every merge. It uses diff-vs-merge-base and needs no task identity, so it is safe to accumulate.
- **CI-equivalent** between merges: `compileall` → `check_portability.py` → `aion scan .` → full `unittest discover`.
- **`freeze`**: owner/Fable only, once, at Wave 7.

| Wave | Contents | Checkpoint after each merge |
|---|---|---|
| 0 **OWNER** | Baseline: 5 module names + `S-22` override + `PROTECTED_PATHS.md` prefix; `check_portability.py` decision | Re-run the 5 blocked PRs' gates; expect green |
| 1 | #23, #22, #13, #32, #31, #15, #25, #16, #19 | CI-equivalent + cumulative anti-dup. Zero overlap, batchable |
| 2 | #28, #26, #20 | Per-branch `strict` pre-merge (#26, #20 touch protected paths); then CI-equivalent |
| 3 `db.py` | #17 → #18 → #35, strictly sequential | Per-branch `strict` pre-merge. After each: fresh bootstrap **and** upgrade-from-`main`-schema, `PRAGMA integrity_check`, `aion health` required checks, skill-registry validation |
| 4 `drive_bridge.py` | #14 → #21 | #14 first turns `macos-readiness` green. CI-equivalent after each |
| 5 `cli.py` | #27 → #29 → #30 → #24 → #33, strictly sequential, **never batch-resolved** | After each: inspect the `cli.py` diff for duplicate subparser registration or handler shadowing; compile; portability; unit tests; CLI smoke on each newly added subcommand. **Stop on first regression** |
| 6 `worker.py` | #34 alone | Per-branch `strict`. Re-read the argv execution boundary diff by hand; confirm `_validate` semantics unchanged |
| 7 **OWNER** | `freeze`, full CI on integration, merge → `main` | |
| 8 | S-11, S-12 (need S-10 landed) · S-25 (needs S-05) · S-03 → S-04 (need S-02) | Normal task flow |

**New bounded tasks** (minimum to correct the architecture; sequenced after Wave 7):
- **S-30** normalize the result contract across `context.py` and `aion_codex_worker.sh`.
- **S-31** result-packet parser plus changed-path governance guard inside the existing worker seam.
- **S-32** findings surface and `errors` linkage.

---

## 3. CODEX WORK-ORDER / RESULT ARCHITECTURE

**Canonical packet = the existing seven fields** (`STATUS`, `ACTIONS`, `FILES_CHANGED`, `TESTS`, `RESULTS`, `BLOCKERS`, `NEXT_ACTION`). Reason: it is the live executor boundary, it is the narrower contract, and narrowing a producer is safer than widening a consumer. S-30 migrates `context.py` to emit exactly these. The four dropped `context.py` fields map without loss: `FAILURES`→`BLOCKERS`, `NEXT_RECOMMENDED_ACTION`+`EXACT_RESUME_POINT`→`NEXT_ACTION`, `RISKS`/`ASSUMPTIONS`→ findings surface (§5), not the packet.

**Work order ← existing task columns.** No new store.

| Work-order section | Source column |
|---|---|
| Objective | `title` + `description` |
| Acceptance | `success_criteria`, `validation_method` |
| Validation command | `validation_command` |
| Deterministic step | `exec_command` |
| Expected artifact | `output_location` |
| Class / deps / blockers | `model_class`, `dependencies`, `blockers` |
| Prior failure | `last_error` |
| Base SHA, allowed/forbidden paths | **envelope metadata only**, carried in the work-order file, not a column |

**Result handling.** Parser is advisory-only and never a completion authority:
1. Parse the 7 fields from `AGENTS/results/<TASK_ID>.md`. Malformed or missing packet → fail the task, record an error, never infer success.
2. Verify `FILES_CHANGED` against the **actually** changed paths (§4). Mismatch, or any governance path touched → reject and revert.
3. **Independently** run `validation_command` via existing `_validate`. This is unchanged and authoritative.
4. `STATUS: DONE` with failing validation → `FAILED`, not DONE. `STATUS: FAILED` with passing validation → still requires `_validate`'s verdict, recorded as a finding.
5. Class A/B with no independent validation keeps returning `needs_review`, per `_validate` today. Do not regress this.
6. `evidence` column is written from the independent validation result, never from packet text.

---

## 4. GOVERNANCE WRITE-PROTECTION

| Layer | State |
|---|---|
| Prompt instruction not to touch governance | **Exists, insufficient alone** |
| `verify_authority.py strict` / `anti-dup` | **Exists**, catches governance edits at gate time |
| Repo-side protected-path + constitutional rules | **Exists** |
| Pre-run changed-state capture (tree hash or `git status` snapshot) | **Must add** (S-31) |
| Post-run changed-path diff vs `FILES_CHANGED` | **Must add** (S-31) |
| Reject + revert on any `AGENTS/prompts/**` or `.lucy/authority/**` touch | **Must add** (S-31) |
| Error + finding recorded on rejection | **Must add** (S-31) |
| Recovery to clean task state | **Must add** (S-31) |
| **True path-level write impossibility** | **UNVERIFIED — owner decision.** `codex exec -s workspace-write` grants the whole workspace. Read-only bind mounts, a narrower sandbox profile, or running Codex against a filtered worktree have **not** been tested on Mark-2 |

**Explicit**: everything above the last row is *detect-and-reject after an attempted write*. That is sufficient for supervised runs. **Unattended Codex should not be enabled on detection alone** until the last row is resolved.

---

## 5. FINDINGS / ERROR LOOP

- Canonical failure state stays in the **`errors` table** (`record`/`resolve`/`classify`/`repeated`). Unchanged.
- **One** append-only review surface: `.lucy/execution/CODEX_FINDINGS.md`. Entry fields: `fingerprint` (deterministic hash of task ID + component + normalised observed text, for dedup), `task_id`, `at`, `expected`, `observed`, `evidence_ref` (path under `AGENTS/results/`), `error_id` (nullable link), `review_status`.
- `review_status` is **written only by planner/owner**. Codex may append a new entry and may never edit an existing one or set status.
- `resume.boot()` surfaces unreviewed findings in the bottleneck line.
- Codex may *propose* instruction changes inside a finding. It may never amend `AGENTS/prompts/**` or `.lucy/authority/**`. Enforcement is §4, not wording.

---

## 6. AUTONOMOUS LOOP V2 DELTA

Changes to existing seams only. No second loop, scheduler, or store.

| Seam | Delta |
|---|---|
| `build_loop.sh` | Add integration-health preflight; refuse to run on a red canonical branch |
| `worker.py` `cloud_command` | Route bounded Codex here with a per-task timeout; add the §3 parser and §4 guard around it |
| `worker.py` `_validate` / `_execution_lock` | **Untouched** |
| `errors.repeated()` | Pause and escalate instead of retrying |
| `resume.boot()` | Surface unreviewed findings in the bottleneck |
| `health.py` | Consume the new nightly evidence producers (history scan, runtime inventory, audit export, encrypted backup, drive check, OpenClaw check) instead of ad-hoc reports |
| Scheduling | Reuse the `learnrepo` lease + stale-lease pattern; add no timer beyond the existing units |

Improvement step = read findings + open errors, propose queue tasks. Never self-amend.

---

## 7. OWNER DECISIONS

1. Wave 0 governance commit (5 module names, `S-22` override, `PROTECTED_PATHS.md` prefix).
2. `check_portability.py`: refine the rule so string-literal denylists stop matching, or add a `KNOWN_EXCEPTIONS` entry owned by S-02.
3. **Codex sandbox policy** (§4 last row): accept detect-and-reject for supervised runs only, or fund true path-level immutability before unattended Codex. **Unresolved; blocks unattended autonomy, blocks nothing else.**
4. Merge integration → `main`, and the post-integration re-freeze SHA.
5. Enabling any unattended loop that can push; branch protection / required checks.
6. `resource_governor.enforce_admission`.
7. Any semantic change to authority, evidence gates, or executor scope.

---

## 8. HANDOFF TO CHATGPT REVIEWER

Verify and expand into Codex-ready repo instructions:
1. Trial-merge each wave into a scratch branch; report any mis-scoped conflict, especially Wave 5's six-way `cli.py` and Wave 3's three-way `db.py`.
2. Confirm the per-branch-`strict` protocol in §2 actually clears every override-using PR (#20, #26, #17, #18, #35, #34), and that cumulative `anti-dup` stays clean across an accumulating branch.
3. Specify the S-30 migration precisely: exact `context.py` emission, and every consumer of the old 11-field names.
4. Specify S-31: snapshot mechanism, changed-path comparison, revert procedure, and where it sits relative to `_validate` so evidence semantics are provably unchanged.
5. Specify the `CODEX_FINDINGS.md` fingerprint function and the append-only guard.
6. Research and report options for §4's last row (sandbox / read-only mount / filtered worktree) on Mark-2, with what each actually guarantees.
7. Confirm nothing proposed introduces a new `aion_core` top-level module, a second scheduler, or a table outside `db.py`.

Do not weaken any gate to simplify integration.
