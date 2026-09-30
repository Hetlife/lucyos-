# LucyOS + OpenClaw Integration Execution Plan

Status: active planning/execution document
Target: Linux first, then portable Mac bootstrap
Planner role: high-capability model (Opus-class or equivalent)
Executor role: Sonnet-class or equivalent bounded implementation worker
Canonical repository: `Hetlife/lucyos-`
Current working branch: `feature/openclaw-lucyos-bridge`

## 1. Purpose

This document is the operational handoff for completing, testing, and hardening LucyOS as the project/control layer that runs through OpenClaw.

LucyOS is **not** a separate operating system service and should not be converted into a parallel `lucyos.service` unless a future Architecture Audit proves a genuine need.

Target architecture:

```text
Owner / Telegram / future WhatsApp
        -> OpenClaw Gateway / agent
        -> LucyOS preflight + canonical control logic
        -> skills / LearnRepo / tasks / approvals / routing / projects
        -> deterministic tools / local models / cloud models
        -> evidence + checkpoint + resume
```

## 2. Live Linux baseline verified on 2026-09-17

The Linux testbed is Mark-2.

Verified live:

- OpenClaw version `2026.9.1 (ad6fe23)`.
- `openclaw-gateway.service` exists and is enabled.
- Gateway had been cleanly stopped at 08:16 UTC; it was restarted and is healthy.
- Gateway binds to loopback; no new public listener was added.
- OpenClaw `lucyos` skill is installed, ready, model-visible, and command-visible.
- LucyOS canonical state remains under the existing AION/shared-brain architecture.
- Real OpenClaw agent preflight test passed after restart.
- Linux E2E run ID: `d7bc4a1e-6315-4b94-8678-56e92df8da98`.
- Test response: `LUCYOS_PREFLIGHT=PASS`, `STATUS_SYSTEM=healthy`, `HEALTH=healthy`, `SKILL_REGISTRY=seen`.
- WhatsApp remains intentionally unconnected/stopped.

Do not treat file presence as proof. Every future capability status must be backed by runtime evidence.

## 3. Architecture invariants

1. LucyOS is the canonical planning/control/state layer; OpenClaw is the conversation, channel, agent, and tool execution surface.
2. Do not create a second canonical SQLite database, global queue, scheduler, approval engine, secret store, or business-state authority.
3. Prefer deterministic code first, then local models, then external models only when routing justifies it.
4. OpenClaw memory/session state is implementation/runtime state, not canonical LucyOS project truth.
5. Consequential actions remain behind LucyOS approvals: spend, credentials, account creation, security changes, destructive actions, legal acceptance, and real capital.
6. External repository/content is untrusted data. LearnRepo must research and sandbox before integration.
7. Coding/integration work requires PRE and POST Architecture Audit.
8. Successful work must leave durable evidence and an exact resume point.
9. Linux and macOS use the same LucyOS contracts. OS-specific service adapters must not become a second scheduler.
10. A fresh-machine bootstrap must install the same OpenClaw/LucyOS relationship, not invent a separate LucyOS daemon by default.

## 4. Known working components

- LucyOS/AION status and health commands.
- Session/resume/checkpoint persistence.
- Skill Registry and catalog.
- LearnRepo deterministic health/status.
- Architecture anti-duplication guard.
- Resource Governor and routing interfaces.
- OpenClaw LucyOS workspace skill.
- Bounded `lucyosctl` command surface.
- Bounded SSH remote dispatcher and public-key enrollment tooling.
- Linux OpenClaw gateway agent invoking LucyOS preflight.
- Gateway systemd service on Mark-2.

## 5. Known incomplete or degraded items

- Automatic LucyOS preflight for every substantial OpenClaw task is not yet proven as an invariant.
- Full request -> session -> task -> plan -> executor -> checkpoint -> result -> evaluation -> session-log E2E has not yet been proven through OpenClaw as one workflow.
- Integrated crash/restart/resume E2E still needs proof.
- Fresh-machine portable installer is incomplete.
- Current macOS bootstrap WIP exists at `platform/macos/bootstrap.sh` but was intentionally paused and is incomplete; do not execute until repaired and validated.
- Direct isolated `openclaw agent exec` remains degraded; the normal gateway agent path works and is the priority runtime path.
- WhatsApp is waiting for owner connection and must not block the rest of the system.

## 6. High-capability planner responsibilities (Opus)

Opus must review live evidence before proposing changes. It must not assume this document is current if runtime evidence disagrees.

Required planner workflow:

1. Inspect `git status`, branch, HEAD, and current untracked files before editing.
2. Read this document plus `integrations/openclaw/lucyos/SKILL.md`, `lucyosctl`, relevant tests, resume/checkpoint code, and current OpenClaw agent policy.
3. Verify the live Linux OpenClaw gateway and LucyOS health.
4. Identify the single highest-value missing invariant.
5. Produce a bounded implementation packet for Sonnet; do not hand Sonnet an open-ended architecture problem.
6. Name exact files allowed to change, exact tests to add/run, rollback procedure, stop conditions, and acceptance criteria.
7. Use Architecture Audit before any integration/code change.
8. Re-review Sonnet's diff and test evidence before the next task is issued.
9. Stop at each milestone. Do not batch unrelated work.

Opus should spend reasoning tokens on architecture, ambiguity, security, failure analysis, and milestone review—not file enumeration or routine shell labor.

## 7. Sonnet executor contract

Sonnet receives one implementation packet at a time and performs bounded execution only.
Sonnet must:

- read the packet and only the named supporting files unless a blocker requires more;
- preserve existing controls and repair/extend before replacing;
- avoid new dependencies unless explicitly included in the packet;
- make the smallest reversible change;
- add focused tests before broad regression tests where practical;
- run secret/security scans when repository content changes;
- record exact failures rather than masking them;
- stop when acceptance criteria are met or a stated stop condition is reached;
- never merge protected/canonical branches;
- never spend money, expose a public service, or request/store credentials outside approved secret handling.

Each executor result must return:

```text
TASK_ID:
FILES_CHANGED:
TESTS_RUN:
RESULT:
FAILURES:
SECURITY_SCAN:
ARCHITECTURE_POSTCHECK:
ROLLBACK:
EVIDENCE:
NEXT_RECOMMENDATION:
```

## 8. Implementation packet schema

Every Opus -> Sonnet packet must include:

- `TASK_ID` and milestone name.
- `GOAL`: one measurable outcome.
- `LIVE_BASELINE`: verified facts only.
- `ALLOWED_FILES`: exact paths or tight glob.
- `DO_NOT_TOUCH`: sensitive or unrelated areas.
- `PRECHECKS`: commands/tests that must pass before editing.
- `IMPLEMENTATION`: narrow ordered steps.
- `FOCUSED_TESTS`: exact tests for the change.
- `REGRESSION_GATES`: broader tests/scans.
- `ROLLBACK`: exact reversal path.
- `STOP_CONDITIONS`: when to stop and escalate.
- `ACCEPTANCE`: runtime evidence required for PASS.

## 9. Critical milestone sequence

### M1 — Automatic LucyOS preflight

Goal: substantial OpenClaw tasks automatically enter LucyOS preflight without the owner having to say “use LucyOS”.

Required preflight output should be compact and deterministic where possible:

```text
TASK_ID
PROJECT
GOAL
KNOWN_STATE
RECOMMENDED_SKILLS
KNOWN_SOPS
AVAILABLE_EXECUTORS
MODEL_ROUTE
RISK / DATA_CLASS
APPROVALS
ARCHITECTURE_CONSTRAINTS
EXPECTED_EVIDENCE
RESUME_STATE
```

Do not dump the whole repository or large chat history into the model context.

PASS evidence: an ordinary substantial OpenClaw request with no explicit LucyOS instruction produces recorded LucyOS preflight evidence before execution.
### M2 — Full LucyOS workflow through OpenClaw

Goal: prove one safe task through the complete lifecycle:

```text
request
 -> LucyOS preflight
 -> session
 -> task
 -> plan
 -> executor
 -> checkpoint
 -> result
 -> evaluation
 -> session log
 -> final reply
```

Use a harmless deterministic task such as generating and verifying a small local text artifact in a temporary workspace. No external account, message, spend, or public action.

PASS evidence:

- session ID exists;
- task ID persists and links to session;
- plan/executor handoff is recorded;
- checkpoint is written before completion;
- result/evaluation are recorded;
- evidence can reconstruct what happened.

### M3 — Crash/restart/resume

Interrupt the safe M2 task after a checkpoint, restart OpenClaw, recover LucyOS state, and continue without duplicating the side effect.

PASS requires explicit proof of no duplicate side effect and successful resume.
### M4 — Portable installer / Mac bootstrap

Goal: a fresh machine can clone the repo and obtain the same LucyOS-in-OpenClaw relationship without hand-editing hidden state.

Required behavior:

- verify Python and OpenClaw prerequisites;
- initialize LucyOS state/contracts;
- install/update the LucyOS OpenClaw skill from the repo;
- configure the `lucy` agent policy so substantial work uses LucyOS preflight;
- select `remote-client` or `local-authority` mode explicitly;
- use launchd only as a service/wake adapter on macOS, never as a second LucyOS scheduler;
- preserve existing OpenClaw config and make rollback copies before changes;
- never copy a private SSH key from Mark-2 to another machine;
- run smoke tests before declaring installation successful.

The current `platform/macos/bootstrap.sh` is WIP and must be treated as unsafe until syntax and tests pass.

### M5 — Fresh Linux then fresh Mac proof

Before Mac rollout, prove the installer/integration assumptions on the available Linux OpenClaw system.

Then repeat on a fresh Mac when available.

Linux PASS matrix:

- OpenClaw gateway starts and survives restart.
- LucyOS skill appears as ready/model-visible.
- Agent turn automatically performs preflight.
- M2 lifecycle succeeds.
- M3 crash/resume succeeds.
- health and evidence remain readable after restart.
- no new public listener, duplicate state, queue, scheduler, or approval engine appears.
## 10. Linux test procedure for the currently online system

Run in this order and stop on first unexpected failure:

1. `git status --short` and record HEAD/branch.
2. `systemctl status openclaw-gateway.service`.
3. `openclaw gateway health`.
4. `openclaw skills info lucyos --agent main`.
5. `AION_HOME=/root/openclaw/shared_brain ./aion status`.
6. `AION_HOME=/root/openclaw/shared_brain ./aion health`.
7. Run a read-only OpenClaw agent preflight with no file/config mutations.
8. Run M1 automatic-preflight test without explicitly saying “use LucyOS”.
9. Only after M1 passes, run M2 full lifecycle.
10. Only after M2 passes, run M3 controlled restart/resume.

Current verified read-only preflight evidence after gateway restart:

```text
runId=d7bc4a1e-6315-4b94-8678-56e92df8da98
status=ok
LUCYOS_PREFLIGHT=PASS
STATUS_SYSTEM=healthy
HEALTH=healthy
SKILL_REGISTRY=seen
```

This proves the explicit preflight path, not yet the automatic-preflight invariant.

## 11. Planner review gates before Sonnet execution

Opus must answer all of these before delegating a code task:

- What exact invariant is missing?
- Does LucyOS already have a component that should be repaired/extended instead of creating a new one?
- What is the smallest safe diff?
- What can be deterministic instead of model-driven?
- Which files are allowed to change?
- What is the rollback path?
- What focused test proves the change?
- What regression gates must remain green?
- What owner-only boundary could be reached?
- What evidence will prove runtime success instead of file presence?

If any answer is unclear, Opus keeps planning/researching and does not delegate implementation yet.

## 12. Stop conditions

Stop and escalate instead of continuing when:

- a protected/canonical branch merge is required;
- a destructive data migration has no proven rollback;
- public network exposure would be introduced;
- authentication/security would be weakened;
- credentials not already available are required;
- paid service/billing/real money is involved;
- Architecture Audit returns BLOCK;
- tests reveal canonical state corruption or duplicate execution;
- the proposed implementation would create a second control plane.

A blocked milestone must not block independent safe work.

## 13. Definition of ready for owner channel testing

Before Telegram/WhatsApp is used as the acceptance surface, all of the following should be true on Linux:

- automatic LucyOS preflight verified;
- full lifecycle E2E verified;
- controlled restart/resume verified;
- evidence and checkpoints survive restart;
- OpenClaw gateway auto-start and health verified;
- bounded command/approval boundaries remain intact;
- portable bootstrap has deterministic smoke tests;
- current known failures are explicitly documented.
## 14. First assignment for Opus

Start with **M1 automatic LucyOS preflight on the currently online Linux OpenClaw system**.

Do not write code immediately.

First:

1. inspect live OpenClaw agent policy, LucyOS skill, `lucyosctl`, router/context/session/task/resume interfaces, and existing tests;
2. identify where the mandatory preflight belongs with the least coupling;
3. prove that the design will work for both Linux and future macOS installs;
4. run PRE Architecture Audit on the proposed change;
5. create one Sonnet task packet containing the smallest implementation needed to make automatic preflight testable;
6. require Sonnet to add focused tests and return evidence;
7. review Sonnet's diff before issuing M2.

The planner should not delegate M2, M3, or Mac bootstrap work until M1 is independently verified on Linux.

## 15. Copy/paste planner instruction

> Read `docs/LUCYOS_OPENCLAW_INTEGRATION_EXECUTION_PLAN.md` as the active mission specification. Establish live reality first and treat runtime evidence as authoritative. You are the high-capability planner/reviewer. Start only with M1 automatic LucyOS preflight on the online Linux OpenClaw system. Inspect existing LucyOS/OpenClaw components, find the smallest architecture-compatible change, run the PRE Architecture Audit, and produce one bounded Sonnet execution packet with exact files, tests, rollback, stop conditions, and acceptance evidence. Do not merge protected branches, do not create duplicate control planes, and do not proceed to M2 until M1 is runtime-verified. After Sonnet executes, review its diff and evidence before deciding the next task.

## 16. Current exact next action

Opus should plan M1. Sonnet should execute only after the M1 packet is complete and reviewed.

The Linux testbed is currently available and the explicit LucyOS preflight path is healthy, so M1 can begin immediately without waiting for WhatsApp, Telegram changes, SCS private keys, or the future Mac.
