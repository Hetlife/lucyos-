# LucyOS master plan: overview, corrections, next steps (2026-09-30)

**Read this file first.** It supersedes the task lists in `SONNET_GET_LUCY_RUNNING_20260930.md`
and `SONNET_FOLLOWUPS_20260930.md`. Keep those for background only: R-01..R-07 are done.
Base `origin/main` @ `5d1c6e5`. Every claim below was checked against the live repo and GitHub
on 2026-09-30.

---

## Status update, 2026-09-30 (later)

- **#75 (R-01) and #76 (R-02) are merged.** `main` is now `d7400b3`, no longer `5d1c6e5`.
  Line numbers in this plan were checked against `5d1c6e5`; re-check any before editing.
- **Deleting a chained PR's base branch made GitHub close the next PR, unmerged.** It happened
  to #76 (after #75) and to #77 (after #76). Both were reopened. No work was lost; the
  original commits were always intact on their branches.
- **Fixed at the root:** every remaining PR (#77, #78, #79, #80) now points straight at `main`
  instead of at its predecessor's branch, so deleting a branch can no longer close another PR.
  All four merge cleanly onto `d7400b3`. Because each contains its predecessors' commits,
  merging #80 alone would bring in the whole stack; merging in order is still the recommended,
  reviewable path. The bad "click Delete branch" advice that started this is corrected.
- #81 (M-01) and #82 (these docs) are independent of the stack.

---

## 1. Where things stand

**LucyOS runs.** A clean clone installs, boots and answers the whole owner surface offline.
`main`: 745 tests OK, and every gate is clean except informational authority drift.

**Open work, all verified green on Linux CI:** a stack of six PRs that must merge in order.

| Order | PR | Task | Tests |
|---|---|---|---|
| 1 | #75 | R-01 real command instead of `aion serve` | 746 |
| 2 | #76 | R-02 owner-setup asks for all bridge variables | 750 |
| 3 | #77 | R-03 public-callback runbook + `bridge_preflight.py` | 758 |
| 4 | #78 | R-04 clean-clone start proof + secret-loading check | 765 |
| 5 | #79 | R-06 Meta bridge optional (OpenClaw is primary) | 769 |
| 6 | #80 | R-07 secrets quoted on write, one shared parser | 784 |

**Owner decisions recorded:** OpenClaw is the primary WhatsApp channel. The `set_secret`
quoting fix was approved and is done (#80). R-05 (`.gitignore`) stays parked until the owner
assigns a task ID.

## 2. Corrections found in this overview

1. **R-07 had been verified but never pushed.** It is now pushed and open as #80.
2. **The red `macos-readiness` job has two separate causes.** It is advisory, so it does not
   block a merge:
   - **5 errors that already fail on `main`**, root-caused. `scripts/duplication_scan.py:100`
     compares a resolved path (`/private/var/...`) against an unresolved `REPO` (`/var/...`).
     `scripts/task_context_profiler.py:28` walks symlink checks *above* the repo root, where
     macOS `/var` is itself a symlink. Both are small, unprotected fixes. This is task M-01.
   - **1 failure introduced by #78**: `test_bridge_start_e2e`. On the macOS runner the bridge
     process stayed alive but was not listening after 15 s, and the cause is unknown because
     the test does not print the process output. This is task M-02.
3. **The plan docs were not on `main`.** They now live together on branch
   `plan/R-followups-20260930` (this branch). Task A-3 opens a docs PR for it.
4. **The owner guide has a placeholder.** `docs/internal/OWNER_STEPS_SIMPLE_20260930.md` (in
   #80) says "(R-07) … I'll give you the number". The number is #80. This is task A-1.
5. **The audit said 7 readers parse secret values. The real number is 5.** This is already
   corrected in #80.

## 3. The other 19 open PRs, triaged and verified

| Verdict | PRs | Evidence |
|---|---|---|
| **Close: content already in `main`** | #2, #4, #5, #6, #7, #8, #9, #10, #24, #27, #29, #30, #33, #34 | Ancestor of `main`, or 0 file differences |
| **Close: duplicate of an already-merged PR** | #50→#66, #51→#67, #52→#68, #56→#69 | `git cherry` shows the patch is in `main`; #52's files are byte-identical |
| **Close: superseded** | #54 | `main` has the newer version via `d6df8c4`; the branch holds 11 stale lines only |
| **Owner decision** | #73 | Real work (context compiler, +851 lines). Merged onto today's `main` it has 0 conflicts, 758 tests OK and every gate clean, **except** `strict`, which refuses it by design: it edits `.lucy/authority/HIGH_MODEL_BASELINE.json` (constitutional) and `aion_core/worker.py` without an override. Owner reads and admin-merges, or rejects. |
| **Owner decision** | #62 | Draft, green CI, prompt work-order lifecycle, not in `main` |
| **Owner decision** | #53 | Draft, green CI, UI/UX docs only |
| **Owner decision** | #11 | 16-Sep authority-gate probe that never ran CI; probably obsolete |

Closing a PR can be undone (reopen). It is still the owner's call. See rule 3.

---

## 4. Tasks for Sonnet, in order

### A-1: fix the owner-guide placeholder (5 min)
On branch `task/R-07-quote-secrets`, in `docs/internal/OWNER_STEPS_SIMPLE_20260930.md`,
replace `(R-07)` with `#80` and remove "(I'll give you the number)". Commit, push to the same
branch (this updates #80). Docs only; no test change.

### A-2: M-01, make the 5 pre-existing macOS errors pass
Branch `task/M-01-macos-symlinked-tmp` **from `origin/main`**, not from the stack.
- `scripts/duplication_scan.py:100`: compare against `REPO.resolve()`, not `REPO`.
- `scripts/task_context_profiler.py:24-31`: resolve `root` once. Apply the symlink check only
  to path components **inside** `root` (stop at `root`; never test its ancestors), and use the
  resolved root in `is_relative_to`. Keep refusing symlinks *inside* the repo, which is the
  point of that check.
- **Reproduce first, on Linux:** make a temp dir, a symlink pointing to it, and run the
  existing tests' scenario with the *symlinked* path as `REPO`/`root`. That is exactly the
  macOS `/var` → `/private/var` layout. Add that as a regression test and see it fail before
  the fix. Add a second test proving a symlink *inside* the repo is still refused.
- Neither file is protected. Run the full suite and every gate. Open a PR against `main`.
- Done when the regression tests pass and the next macOS CI run no longer shows the 5
  `duplication_scan` / `task_context_profiler` errors.

### A-3: docs PR for this plan branch
Open a PR from `plan/R-followups-20260930` to `main`. It is docs only (audit report, entry
point, three plan files). Title: `docs: runnability audit and execution plans (2026-09-30)`.

### A-4: stop, report, wait for the owner
Report A-1..A-3 with PR links and real gate output. **Do not continue to B or C until the
owner has merged #75–#80.**

### C-1: M-02, diagnose the macOS bridge-start failure (only after #75–#80 are merged)
Branch from `main`. In `tests/test_bridge_start_e2e.py`, when the bridge is not listening,
include the child process's stdout/stderr in the assertion message. Extend the deadline to
30 s and poll `check_listening` with a short timeout (e.g. 0.5 s) instead of 3 s. Push, read
the macOS job log, then:
- **slow start**: the longer deadline fixes it. Done.
- **real error in the output**: fix that root cause in the smallest place and report it.
- **never skip or weaken the test.** If it is a runner-only limitation you cannot fix, report
  it with the log excerpt and stop.

### C-2: seeded task text for an OpenClaw owner
`aion_core/seed.py:178` still tells a newly seeded database to
`aion secrets set WHATSAPP_BRIDGE_TOKEN, then start aion-bridge.service`. Change `next_action`
to point at `aion openclaw-check` (OpenClaw is primary), mentioning the direct bridge as
optional. Add or extend a test asserting the seeded text names only commands that exist
(reuse the parser-derived command set from `tests/test_owner_setup.py`). This affects new
databases only.

### C-3: branch-deletion list, prepared but not executed
Re-prove containment against the new `main` using `docs/internal/REPO_CLEANUP_AND_MERGE_PLAN.md`
§1–§3. Produce the list of branches safe to delete, with each tip SHA. **Do not delete.**
The owner approves the list.

---

## 5. Owner only (never delegate)

In plain words, these are also in `docs/internal/OWNER_STEPS_SIMPLE_20260930.md`:
1. Merge #77 → #78 → #79 → #80 in order (#75 and #76 are done). Every one now points at
   `main`, so "Delete branch" is safe. #81 and #82 can merge at any time.
2. On the PC: `cd ~/lucyos && git pull && aion boot && aion status`, then
   **`aion openclaw-check`**. Send both outputs back. Everything about the phone depends on
   this one result; nobody has seen it yet.
3. Say "close them" for the 19 closable PRs in §3, and decide #73, #62, #53, #11.
4. Later: a task ID for R-05; re-freeze authority hashes (5 drifting paths); approve the C-3
   deletion list; a ruling on a bounded restart policy for `aion-bridge.service` (currently
   `Restart=always`, every 5 s).

## 6. Rules (unchanged, absolute)

1. Never weaken, skip or delete a test to get green. The gate wins; report it.
2. Never edit `scripts/verify_authority.py`, `.github/workflows/lucyos-ci.yml`,
   `scripts/check_portability.py`, or anything under `.lucy/authority/`. Never invent a task ID.
3. Never push to `main`, force-push, merge, **close a PR or delete a branch** without the
   owner's explicit instruction in chat.
4. No new third-party dependency. No new `aion_core` module.
5. Never print, log or hard-code a secret value. Build fixtures at runtime.
6. **Gate discipline:**
   - Check real exit codes (`cmd; echo $?`), never `cmd | tail`, which hides failure.
   - Push only after the full suite and every gate are green.
   - Do not delete `evidence/` while the suite runs; it is generated output (R-05).
7. Report the actual output. A step that did not run is reported as not run.
