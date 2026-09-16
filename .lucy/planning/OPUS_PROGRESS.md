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

## UNRESOLVED / IN PROGRESS

- C5 capability matrix against live code (session logging, checkpoint/resume,
  approvals, evidence gates, skills registry, anti-duplication guard, backup,
  local inference) — IN PROGRESS
- C6 model-hierarchy deterministic enforcement — NOT STARTED
- C7 CI presence and clean-machine acceptance gates — NOT STARTED
- C8 Drive / OpenClaw / Mark-2 / Mac readiness — NOT STARTED
- C9 repository visibility recheck — NOT STARTED

## EXACT RESUME POINT

Branch map (C1–C4) is complete and evidence-backed. Resume at **C5**: run the
Q006 test suite locally, then classify each capability in the audit list with
ABSENT/DESIGNED/IMPLEMENTED/TESTED/CI_VERIFIED/DEPLOYED/LIVE_VERIFIED/
DEGRADED/BROKEN/UNKNOWN, citing a file path or a command result for each.
