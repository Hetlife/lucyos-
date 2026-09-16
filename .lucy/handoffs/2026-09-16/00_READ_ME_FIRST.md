# LucyOS Opus → Fable → Sonnet handoff

Date: 2026-09-16
Repository: `Hetlife/lucyos-`
Planning branch: `planning/opus-fable-20260916`
Base branch: `feature/skill-system-q006-architecture-guard`
Verified base commit at setup: `2b59aea7d785bbc42139dcb361834bb48ae158a3`

## Purpose

This branch is a planning and authority-control surface. It is deliberately separate from `main`. Do not merge into `main` without explicit owner approval.

Use the models in this order:

1. **Opus** — audit, reconcile, find gaps, and prepare a compact architect brief. Do not mass-implement.
2. **Owner/ChatGPT cross-check** — sanity-check the Opus brief before Fable.
3. **Fable / highest-capability model** — make final P0/P1 architecture decisions, freeze the high-model contract, create the Sonnet execution queue, and implement only architecture-critical work that should not be delegated.
4. **Sonnet / lower-cost coding model** — execute only bounded work orders from the frozen queue. It may not rewrite high-model architecture, policy, security, approval, routing, governance, or protected planning artifacts.
5. **Fable review** — verify Sonnet diffs against the frozen contract and acceptance tests.
6. **Codex with Mark-2 access** — deploy/configure an exact reviewed commit SHA on Mark-2, run live verification, and report evidence. No architecture invention during deployment.
7. **Owner approval** — only then prepare/approve any consequential merge into canonical `main`.

## Drive evidence

Primary collaboration root: `MARK2_SHARED/05_HANDOFFS`.
Existing coding handoff: `LUCYOS_CODING_AGENT_HANDOFF_2026-09-16`.
Claude/Opus/Fable planning material should be mirrored under:
`MARK2_SHARED/05_HANDOFFS/CLAUDE/LUCYOS_OPUS_FABLE_PLANNING_2026-09-16`.

Drive is collaboration/archive, not LucyOS transactional state.

## Current live-audit facts to REVERIFY before acting

These were established during the 2026-09-16 live audit and may change:

- The Q006 skill-system lineage is ahead of `main` and was running on Mark-2 during the audit.
- The Q006 suite passed 248 tests, while live health exposed a lowercase `f0` → `F0` skill-registry migration mismatch.
- AION session logging, checkpoint/resume, plan ingestion, deterministic execution, local-model execution, approvals, budget-governor handoff, LearnRepo and scheduled worker loops were directly exercised or observed.
- Google Drive bridge code is tested, but Mark-2 Drive uploads were failing while reads worked.
- OpenClaw could run successfully as a temporary loopback gateway, but persistent production integration was not yet live.
- GitHub `main` had no CI workflow during the audit.
- Repository visibility was reported as public. Verify this before storing sensitive material.

Never convert any of these historical facts into current truth without rechecking the live systems.

## Files

- `01_OPUS_READINESS_ARCHITECT_BRIEF_PROMPT.txt`
- `02_FABLE_ARCHITECT_EXECUTION_PROMPT.txt`
- `03_HIGH_TO_LOW_MODEL_AUTHORITY_CONTRACT.md`
- `04_HANDOFF_POINTERS.json`

## Core rule

**High-capability reasoning defines architecture and constraints. Lower-cost executors implement bounded tasks. Executors may not silently alter the reasoning contract. If implementation requires a deviation, stop that task and escalate with evidence.**
