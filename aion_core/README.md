# aion_core/

The control layer. Read in this order; each file has one job and no file
reaches outside its job.

| Module | What it owns | Read it when |
|---|---|---|
| `config.py` | Paths, budget caps, failsafe constants | You need to know where state lives |
| `util.py` | Time, ids, hashes, atomic writes, JSON/JSONL | Never edit state without `atomic_write` |
| `security.py` | Secret detection, redaction, path scanning | Anything touching messages or files |
| `db.py` | SQLite schema, connection, events, idempotency | Adding a table or an idempotent action |
| `tasks.py` | Task queue, ownership, value ranking, evidence gate | Changing how work is chosen |
| `approvals.py` | Tier-3 approval queue and the WhatsApp card | Changing the authority boundary |
| `agents.py` | Agent registry and model routing DET→A→B→C→D | Changing what runs where |
| `errors.py` | Failure capture, classification, lessons | Handling a failure path |
| `memory.py` | Durable facts, decisions, lessons, search, `why` | Storing or recalling knowledge |
| `metrics.py` | Model usage, budget governor, real-vs-modelled money | Anything about cost or revenue |
| `packets.py` | AI sync packet parsing, dedup, conflict flagging | Ingesting external AI work |
| `notebook.py` | The hand-editable `NOTEBOOK.md` and its sync | Human/agent messages into state |
| `sessions.py` | Per-session logs, index, compaction | Recording what a session did |
| `health.py` | Deterministic checks of the real machine | Adding a thing to verify |
| `resume.py` | Checkpoints, `boot()` startup loop, bottleneck | Restart and recovery behaviour |
| `reports.py` | Owner-facing text and generated markdown views | Changing what the owner sees |
| `router.py` | WhatsApp command parsing (no model calls) | Adding or changing a command |
| `context.py` | Task-specific work orders for cheap models | Delegating work downward |
| `backup.py` | Archive creation and real restore verification | Backup policy |
| `bootstrap.py` | Creating/repairing the shared brain, secret store | Adding a directory or seed doc |
| `owner_setup.py` | The single batched owner-action list | A new external dependency appears |
| `fable.py` | Strong-model launch pack and readiness test | Preparing an expensive session |
| `cli.py` | The `aion` command surface | Exposing anything to the terminal |

## Invariants that must not be broken

1. Anything written to state or sent outward passes `security.redact` first.
2. `tasks.complete` refuses empty evidence. Do not add a bypass.
3. Only `router.APPROVE_STRICT` may decide an approval.
4. The database is the truth; markdown is regenerated from it.
5. Every externally-triggered action goes through `db.seen` or a content hash so
   a retry cannot duplicate it.
