# Plan once, execute cheaply forever

The expensive model's job is decomposition, not typing. It emits a PLAN; the
worker loop executes it on deterministic code and local models.

```
strong model  ──emits──>  PLAN (json)  ──aion plan apply──>  dependency-ordered queue
                                                                    │
                                            aion work  ◄────────────┘
                                                 │
              DET: run the command   A: local model   B: cheap cloud   C: left alone   D: approval card
                                                 │
                                        validate → evidence → next task
```

## Commands

```bash
aion plan template            # the schema to fill in
aion plan check plan.json     # refuses any step that cannot be verified
aion plan apply plan.json     # becomes real tasks, dependency-ordered, idempotent
aion work --max 10 --dry-run  # what would run, and where
aion work --max 10            # execute for real
aion capabilities             # what this machine can actually execute now
aion governor                 # apply the budget policy to the queue now
```

## Why a step must carry a check

`plan check` rejects a step with neither a `validation_command` nor a
`success_criteria`. A step nobody can verify can never legitimately be marked
DONE, so accepting one would let the queue fill with unfalsifiable work.

## Command safety

The worker runs only allowlisted command prefixes, and never a forbidden
pattern. Anything else becomes an approval card rather than an execution, so a
plan — written by a model — cannot make this machine run arbitrary shell.
Extend deliberately: `aion allow-command 'make '`.

## Automatic downshift

Spend crosses a threshold and the queue moves down by itself:

| Governor | Effect |
|---|---|
| NORMAL / ARCHITECTURE-DONE | nothing changes |
| SHIFT-DOWN (50%) | queued class C work becomes class B |
| RESERVE (70%) | class B also drops to class A (local, free) |
| CRITICAL-ONLY (85%) / HANDOFF (95%) | as above; discretionary strong use stops |
| STOP (100%) | strong work is held and the owner is told once, in `status` |

Security review, financial reasoning and architecture are never silently
degraded — they are held for a strong session instead. Cost can only fall
automatically; moving work back up is a deliberate act, because it spends money.

A budget ceiling stops **paid** classes only. Deterministic and local work is
free and keeps running, so the system slows down rather than stopping.

## When there is no executor

No Ollama and no cloud worker configured means a class A/B step cannot run. The
loop writes the prepared work order to `AGENTS/work_orders/` and marks the task
WAITING — it does not burn retries against a gap that retrying cannot fix, and
it moves on to other work.

```bash
aion set-cloud-cmd 'claude -p {prompt_file}'   # any CLI you already have authenticated
```
