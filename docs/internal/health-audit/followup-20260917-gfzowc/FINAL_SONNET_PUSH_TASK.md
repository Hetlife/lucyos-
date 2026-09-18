# FINAL-SONNET-PUSH — Verify, Commit, and Push Repaired LucyOS State

Per `LUCYOS_REPO_HEALTH_AUDITOR_TEMP.md` §11 and
`SONNET_REPAIR_APPROVAL_BOUNDARIES_TEMP.md`. This is a verification-first
task, not a blind push command. It has **two parts at two different approval
levels** — read both before starting either.

**Repo-only: YES.** No local-machine, OpenClaw-host, or other out-of-repo
evidence is required or permitted for any part of this task.

---

## Part 1 — Assemble and push the repair branch

**Approval level: B — Sonnet may prepare and push to the *repair* branch; Opus must approve before merge/promotion to `main`**

**Why this level applies:** Multiple subsystems are touched in aggregate
(the reconcile-wave content spans authority, aion_core, bridges, an
OpenClaw integration tree, and planning docs); per
`SONNET_REPAIR_APPROVAL_BOUNDARIES_TEMP.md` Level B, "multiple core files or
subsystems are modified" and "task repairs failed commit/merge history where
patch equivalence must be confirmed" both apply directly. Level B allows
Sonnet to implement on a repair branch and run repo-available tests, but
requires it to STOP before final merge/canonical push.

**Base branch/ref:** `origin/main`
**Expected base SHA:** `0720a9209923bde9652833c4c7a9271041daa855` — if
`origin/main`'s HEAD has moved since this audit, stop and re-verify ancestry
before proceeding; do not assume the SHA above is still current.
**Target repair branch:** `repair/health-audit-promotion-20260917` (new
branch off `origin/main`; do not reuse `merge/reconcile-waves-20260917-chatgpt`
directly as the push target — recreate its content on a fresh branch so the
push carries a proper `Task-ID` trailer, satisfying `verify_authority.py
strict`, which the original branch does not).

### Steps

1. Fetch latest `origin/main`, `origin/audit/health-20260917`,
   `origin/repair/reconcile-20260917`,
   `origin/post-integration/S-30-result-contract`,
   `origin/planning/integration-roadmap-20260917`,
   `origin/feature/openclaw-lucyos-bridge`. Confirm `origin/main`'s SHA
   still matches the expected base SHA above; if not, stop and escalate
   (remote HEAD changed — do not guess through it, per boundaries file
   Commit and Push Boundary step 9).
2. Create `repair/health-audit-promotion-20260917` from `origin/main`.
3. Merge, in order, the same five waves already proven conflict-free on
   `merge/reconcile-waves-20260917-chatgpt`: `audit/health-20260917` →
   `repair/reconcile-20260917` → `post-integration/S-30-result-contract` →
   `planning/integration-roadmap-20260917` → `feature/openclaw-lucyos-bridge`.
   Each merge should be conflict-free (already proven this session); if any
   merge now produces a conflict where the prior pass found none, stop —
   something changed upstream and this is no longer a mechanical replay.
4. Re-apply the `ssh-keygen`-absence test guard exactly as committed on
   `merge/reconcile-waves-20260917-chatgpt` (`a99beeb`) — diff that one
   commit and apply the same change to
   `tests/test_openclaw_lucyos_bridge.py`.
5. Apply TASK-R1 (the 4-module allowlist addition) if not already merged in
   via wave 2 — check first; `repair/reconcile-20260917` already carries
   `57f0e4c`, so this step is likely a no-op. Confirm, don't duplicate.
6. Make **one commit** carrying `Task-ID: FINAL-SONNET-PUSH` as a trailer (or
   ensure the branch name itself satisfies `verify_authority.py strict`'s
   `task/<ID>-...` pattern — the plan doc's own gate commands accept either;
   confirm which one applies by re-reading `scripts/verify_authority.py`'s
   strict-mode task-id detection logic before assuming either form works).
7. Run every command in `FINAL_VERIFICATION_PLAN.md` in full against this
   branch. Record results in
   `docs/internal/health-audit/tasks/FINAL_VERIFICATION_RESULT.md`.
8. Only if every step in `FINAL_VERIFICATION_PLAN.md` passes: `git push -u origin repair/health-audit-promotion-20260917`.

### Sonnet must NOT (Part 1)

- force-push;
- rewrite shared history (all merges above are ordinary merge commits, never rebase);
- push directly to `main`;
- bypass branch protection;
- disable CI;
- use `--no-verify`;
- merge this branch into a protected branch itself;
- ignore a changed remote HEAD (step 1);
- guess through a new merge conflict (step 3/4).

### After pushing Part 1, report

- branch pushed: `repair/health-audit-promotion-20260917`;
- previous remote SHA for that branch name: none (new branch);
- new remote SHA;
- commit SHA(s) added, with the `Task-ID` trailer visible;
- files changed (should match the union of waves 1–5 plus the R1 allowlist,
  nothing else);
- tests executed/results (560 expected, 0 failures/errors, ≤2 skips);
- `anti-dup`/`strict` results (expect 4 remaining violations — ERROR-2/
  semantic_recall only, pending TASK-C1 — and 0 strict violations);
- remaining warnings, explicitly including that ERROR-2 (ISSUE-2/TASK-C1) is
  still open and was not resolved by this push.

---

## Part 2 — Promote to `main`

**Approval level: D — OWNER APPROVAL REQUIRED**

**Why this level applies:** Per `SONNET_REPAIR_APPROVAL_BOUNDARIES_TEMP.md`
Level D, "push/merge directly to protected `main` when not already covered
by an approved workflow" is listed explicitly. Nothing in this repo's
current state constitutes a pre-approved workflow for merging into `main` —
`main` was last touched by an explicit owner commit ("owner: freeze
supervised integration candidate"), which itself signals owner control over
this branch's next move.

**Sonnet and Opus must both stop here.** Part 1's pushed branch and its
verification report are the complete deliverable of this audit and repair
cycle. Do not merge or push to `main` without the owner explicitly approving
this specific promotion, having seen:

- the Part 1 verification report;
- the explicit note that ERROR-2/TASK-C1 (the `semantic_recall.py` SQLite
  question) remains open and unresolved, and whether the owner wants it
  resolved before or after this promotion;
- the `feature/resource-governor` (wave 6) deferral, confirmed still
  deferred, not silently included.

Once the owner approves, the actual merge to `main` (fast-forward or
`--no-ff`, per the owner's stated preference — do not assume) is itself
still bound by every rule in Part 1's "Sonnet must NOT" list, plus: never
merge with `--no-verify`, and re-run `FINAL_VERIFICATION_PLAN.md` step 12
(`git ls-remote origin main`) immediately after to confirm the pushed SHA
matches what was approved.

### After Part 2, report (only after owner-approved push)

- previous `main` remote SHA;
- new `main` remote SHA;
- confirmation every changed file maps to an approved task ID from this
  queue;
- final `anti-dup`/`strict` results against the new `main` baseline itself
  (should now be clean on the allowlist half; ERROR-2 exception should be
  either resolved or explicitly and visibly carried forward as a recorded,
  owner-acknowledged exception, never silently dropped);
- CI status once available;
- explicit statement of what remains open (ERROR-2 if still undecided;
  wave 6/`feature/resource-governor`; the ISSUE-7 side branches).

---

The high-reasoning/audit pass then independently re-verifies the pushed SHA
and diff on `main` before declaring this repair wave complete, per auditor
spec §11's final line. Do not call the repository "healthy" in any summary
until that independent post-push check has actually happened.
