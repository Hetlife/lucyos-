# OPUS_PROGRESS — LucyOS readiness audit

Branch: `planning/opus-fable-20260916`
Started: 2026-09-16
Model: Opus (pre-architect auditor)
Output target: `.lucy/planning/LUCYOS_OPUS_TO_FABLE_ARCHITECT_BRIEF.md`

Rule followed throughout: **verify, do not trust prior documentation.** Every
claim below names the command or file that produced it. Historical facts from
`00_READ_ME_FIRST.md` are treated as claims to recheck, not as truth.

---

## COMPLETED CHECKS

### C1 — Branch inventory and divergence (DONE)

Command: `git fetch origin --prune`, then `git rev-list --left-right --count origin/main...<branch>`
for all 18 remote branches.

| Branch | Ahead | Behind | Last commit |
|---|---|---|---|
| `main` | 0 | 0 | 2026-09-13 |
| `planning/opus-fable-20260916` | 13 | 0 | 2026-09-16 |
| `feature/skill-system-q006-architecture-guard` | 8 | 0 | 2026-09-16 |
| `feature/skill-system-q005-policy-classes` | 7 | 0 | 2026-09-16 |
| `feature/skill-system-q004-learnrepo-contract` | 6 | 0 | 2026-09-16 |
| `feature/skill-system-q003-catalog-lifecycle` | 5 | 0 | 2026-09-16 |
| `feature/skill-system-q002-manifest-schema` | 4 | 0 | 2026-09-16 |
| `feature/skill-system-q001-capability-registry` | 3 | 0 | 2026-09-16 |
| `feature/skill-system-q000-architecture-audit` | 2 | 0 | 2026-09-16 |
| `feature/learnrepo-queue-health` | 1 | 0 | 2026-09-16 |
| `feature/resource-governor` | 1 | 0 | 2026-09-16 |
| `claude/lucyos-architecture-audit-4o4q83` | 11 | 0 | 2026-09-16 |
| `claude/fable-deploy-setup-mc5nr6` | 32 | 31 | 2026-09-10 |
| `claude/aion-whatsapp-control-1seild` | 28 | 31 | 2026-09-05 |
| `arch/lucyos-interface-m-a` | 0 | 2 | 2026-09-13 |
| `candidate/mark2-loop-v1.2-20260908` | 1 | 26 | 2026-09-08 |
| `backup/pre-mark2-loop-v1.2-20260908` | 0 | 26 | 2026-09-04 |
| `feature/lucyos-aion-handoff` | 1 | 37 | 2026-09-04 |

**Verified:** Q000→Q006 is a strictly linear stack, each branch an ancestor of
the next (`git merge-base --is-ancestor` passed for all 7 links).
Q006 HEAD = `2b59aea7d785bbc42139dcb361834bb48ae158a3`, which **matches**
`04_HANDOFF_POINTERS.json:verified_base_commit` exactly. Pointer is accurate.

**Verified:** `feature/learnrepo-queue-health` (commit `75459ad`) is *already
contained* in the Q006 stack. It is not separate work.

**Verified:** `feature/resource-governor` (single commit `1d6aa7e`) is **NOT**
contained in Q006. It is independent work on top of `main`.

**Verified:** `claude/aion-whatsapp-control-1seild` is a strict ancestor of
`claude/fable-deploy-setup-mc5nr6` → superseded, no unique content.

**Verified:** `planning/opus-fable-20260916` = Q006 + 5 planning-only commits
(handoff docs only, no functional code).

### C2 — Duplicate-implementation collision on `aion_core/learnrepo.py` (DONE, P0)

Command: `git show <branch>:aion_core/learnrepo.py | wc -l` and blob-hash compare.

- `main`: file **ABSENT**.
- `feature/resource-governor`: **78 lines**, blob `524abbe2…` — a *third-party
  research registry* (RESEARCH → SANDBOX → SECURITY_REVIEW → BENCHMARK →
  OWNER_APPROVAL → APPROVED/REJECTED), backed by a `research_targets` table.
- `feature/learnrepo-queue-health`: **577 lines**.
- `feature/skill-system-q006-architecture-guard`: **669 lines**, blob
  `38d16b28…` — a *maintenance queue + deterministic health runner* with
  single-node leases. Same lineage as the 577-line version (extends it).

Two unrelated concepts occupy the same module path. Merging
`feature/resource-governor` into the Q006 lineage produces a hard add/add
conflict. A third meaning of the same word exists as the `.claude/skills/learnrepo/`
skill on `claude/lucyos-architecture-audit-4o4q83`.

### C3 — Two governors (DONE, P1)

- `aion_core/governor.py` (103 lines, present on `main` and Q006): spend/₹-driven.
  States: NORMAL, ARCHITECTURE-DONE, SHIFT-DOWN, RESERVE, CRITICAL-ONLY,
  HANDOFF, STOP. Demotes task cost-class; never upgrades.
- `aion_core/resource_governor/` (16 modules, only on `feature/resource-governor`):
  provider-capacity-driven. States: UNKNOWN, EXHAUSTED, CRITICAL, CONSTRAINED,
  CONSERVE, NORMAL, AVAILABLE.

Read the actual integration diff: the new governor is **flag-gated off by
default** (`resource_governor.enforce_admission`), wrapped in try/except so it
cannot break the worker loop, and additive to `resume.py`/`router.py`/`worker.py`.
This is disciplined work, **not** a reckless parallel control plane — but the
*precedence contract* between the two governors is undefined. That is a Fable
decision, recorded in the brief.

Also verified: `.secretscanignore` gains exactly one line
(`tests/test_resource_governor_checkpoint.py`) — a test fixture, legitimate,
but it is a security-surface change and should stay visible in review.

### C4 — Three-way overlap on the critical execution path (DONE, P1)

`aion_core/worker.py` is modified by all three live lineages:
- Q006: +12 lines
- `feature/resource-governor`: +28 lines
- `claude/lucyos-architecture-audit-4o4q83`: +156/-40 lines

Any integration order will require a real merge on the execution path.

---

## COMPLETED CHECKS (continued)

### C5 — Q006 test suite (DONE)
`python3 -m unittest discover -s tests -t . -q` at `2b59aea` → **Ran 248 tests … OK**.
The 248-test claim in `00_READ_ME_FIRST.md` is RECONFIRMED on this exact commit.

### C6 — Skill-registry case migration (DONE, DEGRADED, root cause HIGH)
Reproduced from a clean `AION_HOME`: injecting `cost_class='f0'` yields
`['ai.cloud:invalid-cost']`, and re-running `ensure_defaults()` does **not** heal
it. Root cause: `register()` uppercases on write (`skills.py:115-118`) and
manifest validation is case-insensitive (`skills.py:270`), but
`validate_registry()` is case-sensitive (`skills.py:203`) while the compatibility
migration (`skills.py:163-164`) only maps the word labels none/free/local/external.
Only pre-Q005 rows can carry lowercase — i.e. the live Mark-2 database.
**Invisible to CI because every test starts from a clean DB. LucyOS has no migration test.**

### C7 — The prepared Drive patch is too narrow (DONE)
Read `LUCYOS_STEP1_F0_MIGRATION_FIX.patch` from Drive. It adds `'f0'` to the IN
list plus a regression test. Injected three values it would not heal:
`['ai.cloud:invalid-cost', 'core.health:invalid-data', 'core.state:invalid-risk']`.
`risk_class`/`data_class`/`priority` have no normalization at all. Fix the bug
class, not the instance.

### C8 — Kernel capabilities verified live (DONE)
On a clean `AION_HOME`: `health.run_all()` (14 honest checks),
`backup.create()` + `backup.verify()` → `{'ok': True, 'integrity': 'ok'}` (a real
extract-and-open restore test), `sessions.start()` → `SES-A2475EE4`,
`tasks.create()/update()`, `resume.boot()`, `approvals.create()` → `A-101` →
`decide()` → `APPROVED`. The kernel works and must be preserved.

### C9 — Model-hierarchy enforcement (DONE, P0: NOT ENFORCED)
Four verifications: (a) `architecture.py` is a self-declaration form that never
inspects code; (b) its only caller is the manual CLI `aion architecture-check`
(`cli.py:511-514`); (c) no CI exists on any branch; (d) GitHub API reports
`"protected": false` for all 18 branches including `main`.
Empirical proof: a second governor and a second `aion_core/learnrepo.py` both
landed without the guard firing — it was never asked.

### C10 — CI and repository posture (DONE, P0)
No `.github/` tree on `main`, Q006, `feature/resource-governor`, or
`claude/fable-deploy-setup`. The historical claim was narrower than reality.
Repo metadata re-verified today: `"private": false`, `"visibility": "public"`,
`allow_forking: true`. Secret hygiene itself is good (`./aion scan .` clean,
comprehensive `.gitignore`, no tracked secret files) — but nothing runs the
scanner automatically.

### C11 — Drive context (DONE)
Drive **reads verified live** from this session. Located `MARK2_SHARED`,
`LUCYOS_OPUS_FABLE_PLANNING_2026-09-16` (created today, matches the pointer),
and downloaded two files. `lucyos-ci.yml` is a genuinely good clean-machine
workflow (3.9/3.11/3.14 matrix, compileall, secret scan, full suite, then
init→seed→health→backup→verify-only→fresh-process boot→second health) that has
never been committed. Drive is being used to deliver repository content —
that boundary should be corrected. Uploads unverified from here.

### C12 — Deployment surface (DONE)
9 systemd units (incl. `mark2-drive.*`, `mark2-desktop-commander`). Mac support
is effectively ABSENT: exactly one darwin-aware line repo-wide
(`learnrepo.py:555` returning `"launchd"`), no plists, no Mac install path.

---

## DELIVERABLE STATUS

`.lucy/planning/LUCYOS_OPUS_TO_FABLE_ARCHITECT_BRIEF.md` — **COMPLETE**, all 15
required sections present, decision-grade.

## UNRESOLVED (carried into the brief, §14)

1. Is the repository intentionally public? (blocks P0-3)
2. Mark-2 live state — not reachable from this environment.
3. Drive upload failure — needs a Mark-2 rclone check; only reads verifiable here.
4. OpenClaw — classified UNKNOWN; refused to infer function from filenames.
5. `claude/fable-deploy-setup-mc5nr6` / SEVAACONNECT scope — owner decision.
6. Mac mini — real target or aspiration.
7. Who may push to `main` today.

## EXACT RESUME POINT

Opus audit phase is **complete**. Nothing further should be implemented by this
role. Next actor is **Fable**, starting at brief §15 (`FABLE START HERE`), whose
first decision is the enforcement substrate (P0-2), not architecture.

No functional code was modified by this audit. Only `.lucy/planning/` artifacts
were added.
