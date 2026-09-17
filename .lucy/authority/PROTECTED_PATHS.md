# Protected paths — what lower-cost models may not change, and why

Machine copy: `.lucy/authority/HIGH_MODEL_BASELINE.json` (`protected_paths`).
Enforced by: `scripts/verify_authority.py`, run by the `authority-gate` job in
`.github/workflows/lucyos-ci.yml`. On a pull request the verifier and the
baseline are taken from the **base branch**, so a branch cannot edit the rule it
is being judged by.

## The principle

A lower-cost executor implements bounded tasks. It does not get to redefine the
system it is implementing inside. These paths *are* the definition of the
system — its state, its execution boundary, its money and approval rules, and
the contracts that bind the models. Changing them is a Fable decision landed by
the owner, or a task-scoped exception the baseline records **before** the work starts.

## Constitutional (no task override can ever cover these)

| Path | Why |
|---|---|
| `.lucy/authority/**` | The frozen contract, this file, the baseline, the execution package and `.lucy/authority/LUCYOS_PLATFORM_AND_DATA_CONTRACTS.md` (C1–C10). If a model could edit these, nothing else here would mean anything. |
| `.github/workflows/lucyos-ci.yml` | The pipeline that runs the gates. Removing a job is the same as removing the gate. |
| `scripts/verify_authority.py` | The verifier. Self-explanatory. |

Changing these = a PR that the authority-gate fails on purpose, read and merged
by the owner with admin bypass. That friction is the feature.

## Protected (task override possible, recorded in the baseline by Fable in advance)

| Path | What it owns |
|---|---|
| `.lucy/deployment/**`, `.lucy/handoffs/**` | Deployment contract and the handoff chain |
| `scripts/ci_health_gate.py` | Which health checks CI is allowed to require |
| `scripts/check_portability.py` | The cross-platform ratchet (contract C1). Protected but **not** constitutional: S-11 and S-12 hold task-scoped overrides letting each delete *only its own* `KNOWN_EXCEPTIONS` entry, so the excuse list can shrink under Fable-granted authority and never silently grow. |
| `aion_core/db.py` | Canonical state: every table, every migration |
| `aion_core/resume.py` | The checkpoint/resume contract |
| `aion_core/worker.py` | Execution boundary: what a plan may run, and how work is admitted |
| `aion_core/approvals.py` | Owner-authority state machine |
| `aion_core/security.py`, `.secretscanignore`, `.gitignore` | Redaction, secret scanning, what never enters git |
| `aion_core/governor.py` | Spend policy — the thing that stops LucyOS spending money |
| `aion_core/agents.py` | Model-class routing policy |
| `aion_core/router.py`, `aion_core/config.py` | Owner command surface (incl. safe mode) and budget thresholds |
| `aion_core/architecture.py` | Anti-duplication rules |
| `aion` | The launcher |
| `systemd/**`, `deploy/**` | Service definitions = what runs unattended on a machine |

## Deliberately NOT protected

`cli.py`, `health.py`, `skills.py`, `learnrepo.py`, `memory.py`, `tasks.py`,
`sessions.py`, `plan.py`, `context.py`, `util.py`, `bridges/*`, `tests/**`,
`docs/**`, `skills/catalog/**`, `.claude/skills/**`. Sonnet needs room to do
real work; over-protecting ordinary implementation files just moves every task
into the escalation queue.

## How a task gets an exception

Fable adds `"S-NN": ["path", ...]` to `task_overrides` in the baseline *on the
integration branch* before the task starts. The task branch must be named
`task/S-NN-<slug>` or carry a `Task-ID: S-NN` commit trailer. One task per PR.
The override never extends to constitutional paths.

## What "anti-dup" adds

The Q006 architecture guard asks the proposer whether it added a second
scheduler. The `anti-dup` mode of the verifier reads the diff instead and fails
on: a new `aion_core` top-level module not in the allowlist, a new
`sqlite3.connect()` outside `db.py`/`backup.py`/`drive_bridge.py`, a
`CREATE TABLE` outside `db.py`, a service unit outside `systemd/` or
`deploy/launchd/`, a third-party orchestration import, or a new file named like
a governor/scheduler/orchestrator/approval component. None of these need the
proposer's honesty.
