# START HERE — SEVAA Sales OS under AION

Two repositories, one system. Read this file, then the four below, then stop reading.

| Repository | Role | Where |
|---|---|---|
| `Hetlife/lucyos-` (this repo) | **AION** — the control layer: WhatsApp/phone control, approvals, budget governor, task queue, autonomous worker loop, memory | `aion_core/`, `bridges/`, `directives/` |
| `het-life/sevaaconnect-realestate` | **SEVAA Sales OS** — the first revenue module: FastAPI + SQLite, public `/quote` funnel, founder-gated proposals and Razorpay payment links | `sevaa-sales-os/` inside that repo |

The business-specific plan lives here under `PROJECTS/sevaa-sales-os/` because a standing AION decision forbids hard-coding any one business into the control layer.

## Read in this order, nothing else first

1. `AION_STATE.md` — measured reality as of 2026-09-03
2. `AION_ADVERSARIAL_REVIEW.md` — what is wrong, missing, risky or wasteful
3. `AION_TASK_QUEUE.md` — the execution plan with every task packet in full
4. `MACHINE_HANDOFF.json` — the exact resume point

Then, in the SEVAA repo: `sevaa-sales-os/docs/agent/BOOT.txt`, `CURRENT.md`, `TODO.md`, `state/STATE.json`, `state/ACTIVE_WORK.json`.

## Pointer files (no duplication)

| Directive expects | It lives at |
|---|---|
| `AION_CONSTITUTION.md` | `directives/02_MASTER_AUTONOMOUS_OS_DIRECTIVE.txt` + `directives/03_AGENT_UNLAZY_EXECUTION_STANDARD.txt` |
| `AION_AGENT_ARCHITECTURE.md` | `docs/ARCHITECTURE.md` (AION) + `sevaa-sales-os/docs/spec/ARCHITECTURE.md` (SEVAA) |
| `MULTI_AGENT_PROTOCOL.md` | `sevaa-sales-os/docs/agent/PROTOCOL.md` + `directives/05_SYNC_AND_HANDOFF_PROMPT.txt` |
| `ACTIVE_WORK.json` | `sevaa-sales-os/state/ACTIVE_WORK.json` (authoritative for claims) |
| `AGENT_TASKS.json` | `PROJECTS/sevaa-sales-os/AGENT_TASKS.json` (this folder) |
| `FOUNDER_REQUIREMENTS.md` | `sevaa-sales-os/FOUNDER_REQUIREMENTS.md` |

Task S05 copies thin pointer files into the SEVAA repo so that repo is self-describing too.

## The one rule that governs everything else

Executable reality overrides documentation. Every claim in these files was measured on 2026-09-03 by cloning the SEVAA repo, installing its requirements, and running `pytest` (36 passed) and `scripts/agent_maintenance.py --check` (OK). If a file here and a passing test disagree, the test is right.
