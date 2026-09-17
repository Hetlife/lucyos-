# LucyOS — Repository Cleanup, Merge & Execution Plan

**Written:** 2026-09-17 by the Opus planning pass. **Status:** verified by execution, ready to run.
**Canonical branch:** `origin/main` @ `0720a92`. **Audience:** ChatGPT (planner), Codex (executor), Mark-2 (runtime).

Every claim below was proven by running it, not inferred. Where something is unverified it says so.

---

## 0. Read this first

The repository is **not broken**. `main` is green, carries all 23 S-task branches, and was frozen by
the owner. The problem is **sprawl**: 30 branches, of which 7 carry unmerged work, and no document
said which branch was canonical. That is now recorded in `.lucy/planning/CANONICAL_BRANCH.md`.

Do **not** start by refactoring. Start by merging what is already proven mergeable.

---

## 1. Verified current state

| Fact | Value |
|---|---|
| Canonical branch | `origin/main` @ `0720a92` |
| `supervised/integration-20260917` | identical to `main` (0 ahead, 0 behind) — nothing to do |
| Total remote branches | 30 |
| Branches fully contained in `main` | 13 — safe to delete, listed in §5 |
| Branches with unique work | 7 — merge plan in §3 |
| Full suite on `main` | **537 tests, OK** |
| Full suite on the proven merge stack | **560 tests, 1 environment-only error** (§4) |

### Branches already inside `main` (no action, safe to archive/delete)
`claude/lucyos-architecture-audit-4o4q83`, `feature/learnrepo-queue-health`,
`feature/skill-system-q000`…`q006` (7 branches), `owner/start-here-model-router-20260917`,
`owner/wave0-authority-reconcile-20260917`, `owner/wave0-portability-refinement-20260917`,
`planning/opus-fable-20260916`, `setup/ci-integration-sync-20260916`,
`supervised/integration-20260917`.

---

## 2. The three error classes, and how each is resolved

There are exactly three open problems. Nothing else is failing.

### ERROR-1 — `anti-dup` rejects 4 owner modules (8 violations)
**Cause.** `60b2dc7` (owner-authored) added `model_gateway`, `platform_resolver`, `semantic_recall`,
`usage_telemetry`. The baseline allowlist was never updated. Same omission that blocked five PRs.
**Status.** Already fixed on `repair/reconcile-20260917` (commit `57f0e4c`).
**Resolution.** Merge that branch. The 4 allowlist violations then vanish.
**Note.** `anti-dup` reads the baseline from the *base* branch, so it keeps reporting these until the
fix actually lands on `main`. That is correct behaviour, not a bug. Do not "fix" it twice.

### ERROR-2 — `semantic_recall.py` opens its own SQLite store (4 violations)
**Cause.** Two `sqlite3.connect()` and two `CREATE TABLE` outside `db.py`.
**This is an OWNER DECISION, not a code fix.** Reading the module it is a *rebuildable derived vector
index* (`sqlite-vec` + `fastembed`), which the data contract permits. But nothing records it as
derived, so widening `sqlite_connect_allowed` without that record weakens the rule for everything
that follows.
**Resolution options — owner picks one:**
- (a) add `aion_core/semantic_recall.py` to `sqlite_connect_allowed` **and** record in the data
  contract that it is a rebuildable derived index, never a source of truth;
- (b) teach `anti-dup` to recognise a declared-derived marker (more work, prevents recurrence);
- (c) move the index outside `aion_core`.
**Do not** pick (a) and skip the recording half. That is how a gate quietly dies.

### ERROR-3 — `test_openclaw_lucyos_bridge` errors when `ssh-keygen` is absent
**Cause.** Environment-only. The test shells out to `ssh-keygen` with no availability guard:
`FileNotFoundError: [Errno 2] No such file or directory: 'ssh-keygen'`
at `tests/test_openclaw_lucyos_bridge.py:123`.
**Classification: test bug, not a product bug.** The bridge code is fine.
**Resolution.** Add `@unittest.skipUnless(shutil.which("ssh-keygen"), "ssh-keygen not available")`
to the affected test(s). **Never** delete the test or weaken its assertions.

---

## 3. Merge plan — verified conflict-free unless stated

Each wave: merge, then run §6 gates, then stop if anything fails. **Never force-push. Never rewrite
shared history. Never merge into `main` without the owner.**

| Wave | Branch | Commits | Conflicts | Content |
|---|---|---|---|---|
| 1 | `audit/health-20260917` | 9 | **none (proven)** | Supersedes `integration/consolidation-20260916` entirely: carries its 8 commits **plus** the health-audit docs. Brings in the 4 owner modules. |
| 2 | `repair/reconcile-20260917` | 2 | **none (proven)** | Fixes ERROR-1; adds `CANONICAL_BRANCH.md`. |
| 3 | `post-integration/S-30-result-contract` | 1 | **none (proven)** | `aion_core/context.py` + `tests/test_context_contract.py`. Normalises the result packet. |
| 4 | `planning/integration-roadmap-20260917` | 6 | **none (proven)** | Planning docs only. Zero code. |
| 5 | `feature/openclaw-lucyos-bridge` | 3 | **none (proven)** | New `integrations/openclaw/` tree. **Apply the ERROR-3 skip-guard in this wave.** |
| 6 | `feature/resource-governor` | 1 | **CONFLICTS** | Deferred — see below. |

**Do not merge `integration/consolidation-20260916` separately.** `audit/health-20260917` already
contains all of it. Merging both is redundant and doubles the review surface.

`feature/lucyos-aion-handoff` has an **empty diff** against `main` — its content is already there.
Merge is a no-op; just delete the branch.

### Wave 6 — `feature/resource-governor`, deferred on purpose
Conflicts in `aion_core/cli.py`, `aion_core/db.py`, `aion_core/health.py`. This is the long-known
S-03 case, already documented with a resolution recipe in `.lucy/execution/SONNET_TASK_QUEUE.md`
(keep **OURS** for the `learnrepo.py` add/add; write **THEIRS** to `aion_core/research_registry.py`;
resolve `cli.py`/`db.py`/`health.py` additively keeping both sides). **Do this last, alone, with a
human watching.** Do not batch it with waves 1–5.

---

## 4. Proven result of waves 1–5

A real cumulative merge of waves 1 through 5 onto `main` was executed:

```
conflicts: 0
560 tests, 1 error (ERROR-3, ssh-keygen absent in the sandbox), 1 skipped
./aion scan .                 -> clean
scripts/check_portability.py  -> 0 violations, 3 known exceptions, 0 stale, 55 files, portable
verify_authority.py anti-dup  -> 8 violations (ERROR-1 x4 + ERROR-2 x4)
```

Test count rises 537 → 560. After the ERROR-3 skip-guard lands, expect **560 pass / 0 error**.
After waves 1–2 reach `main`, the ERROR-1 half of `anti-dup` clears, leaving only ERROR-2's four,
which are the owner's ruling.

---

## 5. Branch cleanup

**Only after** waves 1–5 are merged and `main` is green.

Delete the 13 branches listed in §1 (fully contained in `main`), plus `feature/lucyos-aion-handoff`
(empty diff). **Never delete** `main`, or any branch still listed as unmerged in §3, or
`backup/pre-mark2-loop-v1.2-20260908` (an explicit backup).

`integration/consolidation-20260916` may be deleted **only after** wave 1 is merged and verified,
since `audit/health-20260917` is what actually carries its content forward.

Deleting a branch is an owner action (`owner_only_actions` includes "delete branches or tags").
Codex proposes the list; the owner runs the deletions.

---

## 6. Gate commands — run after every wave, no exceptions

```bash
git status --short | grep -E '^(UU|AA|DU|UD)'     # must be empty
python3 -m compileall -q aion_core bridges tests scripts
python3 -m unittest discover -s tests -t . -q     # must not drop below the previous wave's count
./aion scan .                                     # must be clean
python3 scripts/check_portability.py              # portable, 0 stale
python3 scripts/verify_authority.py anti-dup --base origin/main
python3 scripts/verify_authority.py strict  --base origin/main --branch "$(git branch --show-current)"
```

**`strict` will fail on any commit touching `.lucy/authority/**`.** That is by design:
`.lucy/authority/**` is *constitutional*, and no task override, no branch name and no `Task-ID:`
trailer can ever clear it. Such a change is merged by the **owner with admin bypass**. Do not try to
make it pass. Do not edit `scripts/verify_authority.py`. Do not invent an `S-NN` id to slip past the
regex. Recording the failure honestly is the correct outcome.

---

## 7. Hard rules for every agent

- Never weaken, skip, disable or quarantine a test to get green CI. Fix the cause or report it.
- Never edit `scripts/verify_authority.py`, `.github/workflows/lucyos-ci.yml`, or anything under
  `.lucy/authority/**` to make a check pass.
- Never force-push, rewrite shared history, or push to `main`. The owner merges to `main`.
- Never add a new `aion_core` top-level module, a second scheduler, or a `CREATE TABLE` outside
  `db.py` without a baseline entry — `anti-dup` rejects all three mechanically.
- No spending, no credential handling, no external account creation, no real-capital action.
  Strategy Factory stays paper/sandbox only.
- Never claim a test passed without running it in that session.
- If the remote HEAD moves mid-execution, **stop and escalate**. Do not re-plan a merge alone.

---

## 8. Role split

**ChatGPT (planner).** Verifies this plan against the live repo, sequences the waves, decides when a
wave is safe, and escalates the owner decisions. Does not write bulk code.

**Codex (executor).** Executes one wave at a time from an explicit work order. Runs §6 after each.
Reports the seven-field packet: `STATUS / ACTIONS / FILES_CHANGED / TESTS / RESULTS / BLOCKERS /
NEXT_ACTION`. Stops rather than improvising. May **append** findings to
`.lucy/execution/CODEX_FINDINGS.md`; may never amend its own governing instructions.

**Mark-2 (runtime).** Runs nothing from this plan automatically. The scheduled Routines are
currently **paused** (LucyOS daily cheap loop, LucyOS interface continue, LucyOS weekly strong
review — all disabled 2026-09-17). Re-enable only after `main` is green and the owner says so.

---

## 9. Owner decisions blocking completion

1. **ERROR-2 ruling** — which of options (a)/(b)/(c) in §2.
2. **`model_gateway` external providers** — `openrouter.ai`, `api.groq.com`, `api.cerebras.ai`.
   Default-deny (`data_class` defaults to `INTERNAL`), auxiliary to the existing executor hierarchy,
   learnrepo vetting manifests exist. Ratify, restrict, or disable until Mac migration.
3. **Merge each wave into `main`** and set `origin/HEAD` to `main` (currently unset).
4. **Branch deletions** in §5.
5. **Re-enabling the paused Routines.**

Nothing else needs an owner. Waves 1–5 and the ERROR-3 fix are ordinary engineering.
