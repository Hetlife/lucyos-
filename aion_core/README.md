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


## Task reliability (Phase A+B)

`tasks.update` validates transitions against `TRANSITIONS`; direct READY → DONE
is invalid even with evidence. Existing `tasks.complete(id, evidence)` callers
retain an atomic, audited reconciliation path through NEEDS_REVIEW. DONE requires
explicit evidence, completed dependencies and no unresolved approval. Terminal
records are immutable except that legacy DONE preparation may acquire a new
pending approval linked to that task; this clears completion time and holds the
action until the owner decides. Duplicate completion with identical evidence is a no-op.

For already implemented git work, use
`tasks.close_implemented(task_id, full_commit_sha, repo=repo_path)` against the
canonical runtime database. This does not rerun `exec_command`. It requires a
clean tree at that exact HEAD, a matching `Task-ID:` commit line, success criteria
and a task `validation_command` that independently verifies those criteria. It
runs that validation, secret scan, portability, authority and anti-dup gates,
then stores commit and command results as JSON in the existing task evidence.
Repeated closure returns `False` without changing the record. Missing proof,
changed task/tree, active ownership, cancelled tasks, owner/architecture holds
and conflicting closure evidence are refused. No packet claim closes a task.
Older commits must be reconciled against a suitable clean checkout explicitly;
this helper does not switch branches, deploy, or change architecture authority.

`heartbeat(id, owner_agent)` only refreshes contact (`updated_at`).
`record_evidence(id, proof, kind="artifact"|"validation"|"git", owner_agent=...)`
stores a measured observation and a timestamped `task.evidence` event in the
existing database. Repeating identical proof is not progress. `progress(id)`
reports evidence stalls even when contact continues; `reports.status()` includes
the count. Legacy free-text evidence has no inferred progress timestamp. Stale
owner release uses contact and is bounded by `MAX_TASK_RETRIES`; a live stalled
worker is reported, not concurrently re-executed.

`classify_failure` and `recovery_for` define ordered deterministic recovery data.
The existing worker calls `tasks.fail`: quota waits, context/architecture require
review, provider schema errors require review, missing routes wait for an executor,
owner boundaries require approval, and process death/heartbeat loss/app-server/test/timeout/unknown
failures have bounded retries. Existing cloud timeout holds preserve partial work
without spending retries and no longer masquerade as missing-executor holds.
These APIs add no queue, scheduler, schema migration or background loop.
