# directives/

The owner's canonical prompt bundle, preserved verbatim. These files are the
**authority layer**: the code in `aion_core/` implements them, and where the two
disagree the directive wins and the code is a bug.

| File | When it is used | Who reads it |
|---|---|---|
| `00_READ_ME_FIRST.txt` | Orientation and the instruction hierarchy | Every agent, first |
| `01_START_FABLE_BOOTSTRAP.txt` | Opening a strong-model build session | The strong model |
| `02_MASTER_AUTONOMOUS_OS_DIRECTIVE.txt` | Standing project-level rules | Every agent |
| `03_AGENT_UNLAZY_EXECUTION_STANDARD.txt` | Default for every worker and sub-agent | Every worker |
| `04_LOW_COST_WORKER_PROMPT.txt` | Ollama and cheap-cloud execution | Class A and B workers |
| `05_SYNC_AND_HANDOFF_PROMPT.txt` | Moving work between AI sessions | Any external session |
| `06_RESUME_AND_RECOVERY_PROMPT.txt` | A session restarts or loses context | The resuming session |
| `07_OWNER_APPROVAL_AND_WHATSAPP_PROMPT.txt` | Approval gating and mobile control | Orchestrator |
| `08_FINAL_PRE_FABLE_LAUNCH_DIRECTIVE.txt` | Preparing before spending on a strong model | Coordinator |

## Instruction hierarchy

Law and platform safety, then the owner's current instruction, then the master
project objective, then `02`, then this control layer, then project directives,
then the agent role, then the current work order, then historical notes. A lower
layer never silently overrides a higher one.

## Where each rule is enforced in code

| Directive rule | Enforced by |
|---|---|
| No secrets in state, git, logs or WhatsApp | `aion_core/security.py`, `aion scan` |
| DONE requires evidence | `tasks.complete` refuses an empty evidence string |
| One approval holds one action only | `approvals.create` touches just its own task |
| Casual talk is not authorization | `router.APPROVE_STRICT` |
| Cheapest capable model wins | `agents.route`, `agents.escalate` |
| Real money is separated from forecasts | `metrics.record_money` stages |
| Budget governor thresholds | `metrics._governor`, `fable.budget` |
| Duplicate work is never applied twice | `db.seen`, packet content hashing |
| Never idle on one blocker | `tasks.ready` skips gated tasks |
| Exact resume point survives a crash | `resume.checkpoint`, `resume.boot` |
