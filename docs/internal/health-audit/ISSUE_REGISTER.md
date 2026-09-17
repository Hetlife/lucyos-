# Issue Register — 2026-09-17

Severity per `LUCYOS_REPO_HEALTH_AUDITOR_TEMP.md` §5 (P0 security/destructive
> P1 core-runtime/authority > P2 material functional > P3 reliability > P4
cleanup). No severities inflated; see evidence column for the check that
produced each entry.

| ID | Sev | Subsystem | Classification | Summary | Evidence | Repair task |
|---|---|---|---|---|---|---|
| ISSUE-1 | P1 | `.lucy/authority` / governance | product bug (baseline omission) | 4 owner-authored `aion_core` modules (`model_gateway`, `platform_resolver`, `semantic_recall`, `usage_telemetry`) are not in `HIGH_MODEL_BASELINE.json`'s allowlist on `main`, so `verify_authority.py anti-dup` fails for any branch carrying them, even though a fix already exists | `verify_authority.py anti-dup --base origin/main` on the reconcile-wave branch: 4 of 8 violations are exactly these modules; fix already committed at `57f0e4c` on `repair/reconcile-20260917` | TASK-R1 |
| ISSUE-2 | P2 | `aion_core/semantic_recall.py` / persistence | governance / owner decision, not a code bug per se | Module opens its own SQLite connection and issues `CREATE TABLE` outside `aion_core/db.py`, which `PROTECTED_PATHS.md` names as sole owner of "every table, every migration" | `verify_authority.py anti-dup`: 4 of 8 violations, 2× `sqlite3.connect()`, 2× `CREATE TABLE`, both outside `db.py` | TASK-C1 (Level C — stop for high-model/owner approval before any code change) |
| ISSUE-3 | P1 | repo integration state | governance / process | The only verified-green, conflict-free reconciliation of `main` + all pending work (`merge/reconcile-waves-20260917-chatgpt`) has never been pushed to `main`; this is the actual blocker on calling the repo "healthy", not any remaining code defect | Ancestry check: `origin/main` is an ancestor of the reconcile-wave branch, not the reverse; ISSUE-1 and ISSUE-2 are the only two things preventing a clean `anti-dup` on that branch | TASK-R2 / FINAL-SONNET-PUSH (Level D — owner approval to touch `main`) |
| ISSUE-4 | P1 | reconcile-wave branch itself | governance / process | `verify_authority.py strict` fails on the reconcile-wave tip because a multi-wave merge commit doesn't carry a single declared `Task-ID:` trailer or `task/<ID>-...` branch name | `verify_authority.py strict --base origin/main --branch a99beeb...`: 1 violation, "protected paths changed but task id is undeclared" | Addressed as a completion criterion in FINAL_SONNET_PUSH_TASK.md, not a separate repair |
| ISSUE-5 | P4 | branch hygiene | stale claim in prior audit doc | `repair/reconcile-20260917:docs/internal/REPO_CLEANUP_AND_MERGE_PLAN.md` asserts `feature/lucyos-aion-handoff` has an "empty diff" against `main`; re-checked this session and its tip commit is not a literal ancestor of `main`, and a plain `git diff` now shows hundreds of files' difference (expected, since `main` has grown substantially since that claim was written) | `git merge-base --is-ancestor origin/feature/lucyos-aion-handoff origin/main` → NO; `git diff origin/feature/lucyos-aion-handoff origin/main --stat` → 365 files changed | TASK-R3 (evidence-gathering only, no code change) |
| ISSUE-6 | P4 | local clone config | cosmetic | This clone's `refs/remotes/origin/HEAD` symbolic ref is unset; the actual GitHub remote default branch is correctly `main` (`git remote show origin` confirms) | `git symbolic-ref refs/remotes/origin/HEAD` fails locally; `git remote show origin` succeeds and reports `main` | No repo action; per-clone `git remote set-head origin -a` if desired. Not queued. |
| ISSUE-7 | P4 | 7 side branches (see HEALTH_REPORT.md §5) | UNVERIFIED — not yet audited | `claude/aion-whatsapp-control-1seild`, `claude/fable-deploy-setup-mc5nr6`, `feature/context-pack`, `plan/lucyos-openclaw-e2e`, `test/authority-gate-positive-20260916`, `candidate/mark2-loop-v1.2-20260908` carry unmerged, unaudited content not on the critical path | `git log --oneline origin/main..origin/<branch>` counts in HEALTH_REPORT.md §5 | Not queued this pass — recorded so a future audit doesn't rediscover them from zero |
| ISSUE-8 | — (not an issue) | `feature/resource-governor` (wave 6) | correctly deferred, not a defect | Real merge conflicts in `aion_core/cli.py`, `aion_core/db.py`, `aion_core/health.py`; resolution recipe already documented in `.lucy/execution/SONNET_TASK_QUEUE.md` per the prior plan | `git merge-base --is-ancestor` shows it's absent from both `main` and the reconcile-wave branch; conflict claim not independently re-attempted this session (would require a real merge attempt against protected files — Level C/D territory, out of scope for a planning-only pass) | TASK-C2 — do last, alone, human-watched, per prior plan; not auto-executable by Sonnet |

## Findings NOT made (explicitly, to avoid manufacturing work)

- No P0 findings. `./aion scan .` clean; no unsafe `shell=True`/`eval`/`exec`/bare-except
  in core paths; no credential exposure found.
- No broken imports, circular imports, or dead entrypoints found on the
  reconcile-wave branch — `compileall` across `aion_core`, `bridges`,
  `tests`, `scripts` is clean and the full test suite collects and runs
  (560 tests) without collection errors.
- No test suite regressions: test count only grows across every wave
  (420 / 537 on the two pre-merge branches → 560 combined), and the run is
  `OK` with 2 skips, 0 failures, 0 errors.
- No evidence any safety/authority gate was weakened to get to this green
  state — `anti-dup` and `strict` were run for real, not bypassed, and both
  correctly still report their (expected, already-understood) violations.
