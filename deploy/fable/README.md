# Fable launch pack

Everything a strong-reasoning session needs, and nothing it doesn't. Committed
here because the live pack lives in `<AION_HOME>/FABLE/`, which is machine
state — it does not survive a rebuilt machine, and it cannot be read from a
phone. Regenerate the live copy any time with `aion fable-pack`; this is the
durable one.

## How to start the session

1. Add **INR 700** of credit. That is phase 1's whole ceiling, not a target.
2. Open a fresh strong-model chat.
3. Paste **`FABLE_OFFLINE_PROMPT.txt`** as the first message.
4. Attach these five files to that same message:
   - `FABLE_CONTEXT.md`
   - `FABLE_TASK_QUEUE.md`
   - `FABLE_DECISIONS.md`
   - `FABLE_COMPLETION_CRITERIA.md`
   - `PLAN_FORMAT.md`
   - `MISSION_AND_MILESTONES.md`

The repository is private, so the session cannot fetch anything — the prompt
says so explicitly and tells it to mark gaps `UNKNOWN` rather than invent
them. Attaching the files is what makes the session possible.

## What comes back

Three artifacts, in this priority order if the budget runs out early:

| # | File | What it must contain |
|---|---|---|
| 1 | `EXPERIMENT.md` | One offer, one channel, one buyer. Hypothesis that can be false, unit economics, cost ceiling, time window, success and failure conditions **as numbers**, and the decision each outcome forces. |
| 3 | `plan-<name>.json` | Executable steps matching `PLAN_FORMAT.md` — every step verifiable, C class only where genuinely needed. |
| 2 | `MILESTONE_LADDER.md` | Which rung is the real wall, and where capital must enter. |
| 4 | `SECURITY_REVIEW.md` | Only if budget remains. Concrete failing scenarios, not categories. |

## What to do with them

```bash
mkdir -p ~/lucyos/incoming
# save each artifact there, then:
aion plan check incoming/plan-<name>.json     # rejects any unverifiable step
aion plan apply incoming/plan-<name>.json     # queues it for the cheap loop
```

`plan check` is a real gate, not a formality — it refuses steps that lack a
`validation_command` or `success_criteria`. If it rejects the plan, that is the
strong model's error to fix, not something to work around.

## Phase 2

Phase 2 (**INR 1,300**, on-machine execution) only becomes relevant once phase
1's artifacts exist and have been applied. Switch with `aion fable-phase 2`,
which regenerates this pack with on-machine criteria. Cumulative hard ceiling
across both phases is **INR 2,000** — the governor enforces it, and
`set_phase` can no longer quietly raise it.
