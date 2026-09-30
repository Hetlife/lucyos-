# Coding-agent entry point — LucyOS, 2026-09-30

One file to route from. **Read this, then exactly one plan file. Do not read the whole repo.**

**Base:** `origin/main` @ `5d1c6e5` · **Goal:** get LucyOS answering on the owner's phone.

---

## First command, before anything else

```bash
git rev-parse --short origin/main
```

- **`5d1c6e5`** → everything below is current. Proceed.
- **anything else** → the code findings are probably still true, but re-verify any line number
  before editing it, and say in your report that the base moved.

---

## The one thing to understand first

**LucyOS is not half-built. It already runs.** From a clean clone, `scripts/install.sh`
finishes in ~2 minutes, seeds 9 tasks, takes and restore-tests a backup, and reports
`healthy`. 745 tests pass. All gates are clean except a known informational authority drift.

The gap is the phone: the bridge service cannot start on a fresh machine because owner-setup
never asks for the variables it requires.

**So your job is not to build or refactor anything. It is to close four specific gaps.**
Treating this as a "fix the codebase" task is the main way to waste the owner's money here.

---

## Where everything is

| What | Path | Use it for |
|---|---|---|
| **Your task list** | `.lucy/execution/SONNET_GET_LUCY_RUNNING_20260930.md` | **Start here.** R-01..R-05, with exact files, line numbers and tests. |
| Evidence behind it | `docs/internal/LUCYOS_RUNNABILITY_AUDIT_20260930.md` | Why each task exists; what was proven by execution. |
| Owner run path | `TOMORROW.md` | The 5-step path the owner follows. R-01/R-02 fix where it breaks. |
| Repo router | `START_HERE.md` | Which seams exist; what never to rebuild. |
| Authority rules | `.lucy/authority/HIGH_MODEL_BASELINE.json` | Protected + constitutional paths. Read before touching any of them. |
| Repo-health findings | `docs/internal/CODE_REVIEW_20260924.md` | Branch sprawl, readability, logging. **Out of scope this week.** |
| Branch triage method | `docs/internal/REPO_CLEANUP_AND_MERGE_PLAN.md` | Only if the owner asks for cleanup. |

---

## Already proven — do not re-verify, do not "improve"

Measured on a clean clone at `5d1c6e5`. Re-running these is the second-biggest token sink.

- `scripts/install.sh` → exit 0, 65 paths, 8 decisions + 9 tasks, backup made and
  restore-tested, reports `healthy`.
- `aion status | tasks | milestones | boot | fable-ready | owner-setup` → all work.
- `whatsapp_bridge.py stdin` → status / money / tasks / help all answer.
- **745 tests pass (2 skipped)**, 129s.
- `./aion scan .` clean · `check_portability.py` 0 violations / 0 stale / 59 files ·
  `verify_authority.py anti-dup` 0 violations.
- `verify_authority.py self` reports **5 hash drifts** (`lucyos-ci.yml`, `config.py`, `db.py`,
  `router.py`, `security.py`). **Known, informational, owner business.** Do not fix. Do not
  re-freeze.
- `evidence/boundary_report.md` shows 2 warning-mode `sqlite_import` findings. That is the
  S-48 ratchet working as designed (commit `0f1b8e3`), not a regression.

---

## Out of scope — do not touch this week

Branch cleanup (124 branches, 59 unmerged), the readability reformat, access logging,
`aion_core` module growth, and the authority re-freeze. All are tracked in
`CODE_REVIEW_20260924.md`. They are real, and none of them blocks the phone. Pulling them in
holds the owner's actual goal behind repo hygiene.

---

## Hard rules

1. Never weaken or skip a test to get green. A gate that blocks you has done its job — report
   it, do not route around it.
2. Never edit `scripts/verify_authority.py`, `.github/workflows/lucyos-ci.yml`, or anything
   under `.lucy/authority/`. These are constitutional; `strict` refuses them unconditionally.
3. **Never invent a task ID** to satisfy the verifier. If a protected path needs an override
   that does not exist, stop and say so.
4. Never push to `main`. Never force-push. Never merge. Open the PR and stop — the owner merges.
5. One task per branch, one task ID per PR, so `strict` can pass.
6. No third-party dependencies. LucyOS core is Python standard library only.
7. No new `aion_core` module — `anti-dup` will catch it, and module growth is a tracked finding.
8. Never bind the bridge to `0.0.0.0`. Loopback plus a tunnel is the design.
9. Never read, print, log or hard-code a secret value, including in test fixtures.
10. Report honestly. If a step did not run, say it did not run. A report that says "fine" when
    it is not is worse than no report.

---

## What the owner must do (never delegate these)

- Supply the WhatsApp Cloud API values on the PC via `aion secrets set`.
- Choose a tunnel provider, and pay for it if it costs anything.
- Add INR 1000 strong-model credit (`aion fable-ready` recommends it; INR 2,000/month ceiling,
  enforced by the budget governor).
- Re-freeze authority hashes to clear the 5-path drift.
- Merge every PR.

---

## Finish with

1. Per task: branch, PR link, what you ran, actual output.
2. Test count before and after — it must not drop below 745.
3. What you did not do, and why.
4. Anything in the audit that turned out to be wrong. **The repository wins over the audit.**
   I would rather be corrected than agreed with.
