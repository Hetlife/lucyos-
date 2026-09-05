# FABLE CONTEXT

_Measured 2026-09-05T15:14:43+00:00. Every line below was checked, not assumed._

## Owner objective
WhatsApp is the steering wheel, OpenClaw is the driver interface, AION is the brain,
specialist agents are the workforce, the Ubuntu PC is the permanent office. The owner
sends `status` in the morning and `report` in the evening and is contacted in between
only when something genuinely needs human authority.

## Architecture
iPhone/WhatsApp -> OpenClaw bridge -> AION router (deterministic) -> task queue ->
model routing (deterministic / local / cheap cloud / strong) -> agents -> tools.
State: SQLite at `state/aion.sqlite3` (truth) + generated markdown views.

## Machine state (measured)
- `database`: OK — integrity=ok, 9 tasks, fts=on
- `shared_brain`: OK — complete
- `disk`: OK — 32.07 GB free at /root/openclaw/shared_brain
- `sync_inbox`: OK — 0 pending, 0 failed, 0 processed
- `task_queue`: OK — 6 ready, 0 running, 0 blocked, 0 stale claims released
- `errors`: OK — 0 unresolved
- `budget`: OK — day ₹0/200.0, month ₹0/2000.0, governor NORMAL
- `git`: OK — branch claude/aion-whatsapp-control-1seild, 1 uncommitted paths
- `ollama`: OK — not installed here — local-model routing degrades to class B
- `network`: OK — outbound reachable
- `secret_store`: OK — /root/openclaw/shared_brain/private_state/secrets.env mode 0o600 (must be 0o600)
- `backup`: OK — latest aion-backup-20260904T182358+0000.tar.gz (30.0 KB)

## Model routing

- **DET** — deterministic code — exact, repeatable, zero model cost
- **A** — local model (Ollama) — classification, extraction, formatting, summarising
- **B** — cheap cloud model — routine coding, standard research, normal structured work
- **C** — strong reasoning model — architecture, hard debugging, security, economics
- **D** — owner — a genuine human decision boundary

## Agents registered

- `ollama-local` class A · llama3.1:8b · reliability 1.0
- `cloud-cheap` class B · claude-haiku-4-5-20251001 · reliability 1.0
- `cloud-sonnet` class B · claude-sonnet-5 · reliability 1.0
- `cloud-strong` class C · claude-opus-5 · reliability 1.0
- `owner` class D · human · reliability 1.0
- `openclaw` class DET · openclaw · reliability 1.0

## Security model
- Secrets live only in `private_state/secrets.env` (0600), entered on the PC.
- `security.redact` runs on every write to state and every outbound message.
- Inbound WhatsApp messages containing credential-shaped text are refused, not stored.
- `aion scan` blocks credential-shaped content before a commit.

## Task and memory state
- Task counts: {'DONE': 3, 'READY': 6}
- Packets ingested: none yet
- Open errors: 0
- Pending approvals: none

## Budget
- Cumulative authorization INR 2000; used INR 0; remaining INR 2000; governor NORMAL.

## Current bottleneck
no validated revenue experiment exists yet

## Exact starting action
work TASK-1BB538FF: Read FABLE_CONTEXT.md, then write the experiment
