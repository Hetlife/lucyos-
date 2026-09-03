# Architecture

```
iPhone / WhatsApp          the owner: approvals and steering, never secrets
        |
OpenClaw bridge            bridges/whatsapp_bridge.py — transport only
        |
AION router                aion_core/router.py — deterministic, no model needed
        |
Task queue + state         aion_core/tasks.py, db.py — SQLite is the truth
        |
Model routing              aion_core/agents.py — DET -> A -> B -> C -> owner
        |
Agents / tools             local model, cheap cloud, strong model, shell, git
        |
Verified real-world result evidence recorded against the task
```

## Why the router is deterministic

`status`, `money`, `approve A-142` and the rest are regular expressions and SQL.
No model is called to answer them. The control channel therefore keeps working
when every provider is down, when the budget governor has stopped spending, and
when the network is out. Models are used for work, not for reading commands.

## State model

The database at `<AION_HOME>/state/aion.sqlite3` is the single source of
operational truth. Every markdown file in the shared brain is a generated view,
rewritten by `aion sync-docs`. That is why hand-editing them is pointless: the
next render overwrites the file. Change state through the CLI.

Tables: `tasks`, `agents`, `approvals`, `packets`, `errors`, `model_usage`,
`finance`, `decisions`, `memory` (+ FTS index), `events`, `idempotency`, `meta`.

## The four boundaries that are enforced mechanically

1. **Secrets.** Every write to state and every outbound message passes through
   `security.redact`. Inbound messages containing credential-shaped text are
   refused before they touch state. `aion scan` blocks a commit.
2. **Evidence.** `tasks.complete` raises unless given a non-empty evidence
   string, so "code written" can never be recorded as DONE.
3. **Authority.** Only the exact form `APPROVE <ID>` or `DENY <ID>` decides an
   approval. "sounds good" does nothing.
4. **Cost.** Every model call is recorded; the governor moves through NORMAL,
   ARCHITECTURE-DONE, SHIFT-DOWN, RESERVE, CRITICAL-ONLY, HANDOFF and STOP as
   the strong-model budget is consumed.

## No-idle rule

An approval holds exactly one task. `tasks.ready` ranks everything else by
expected value, so a pending approval never freezes the system.

## Failure loop

`errors.record` classifies a failure by pattern, `tasks.fail` retries twice and
then blocks, `agents.escalate` moves one step up the model ladder rather than
looping, and `errors.resolve` writes the lesson into searchable memory.

## Resume

`resume.boot` verifies the shared brain, ingests the sync inbox, releases stale
claims, checks approvals and failures, runs health, and names the current
bottleneck. It reports the previously recorded next action rather than blindly
re-running it, which is what the recovery directive requires.
