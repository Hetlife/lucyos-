# incoming/ — executable plans from the strong session

Each file is a PLAN in the schema of `deploy/fable/PLAN_FORMAT.md`, checked by
`aion plan check` (rejects any unverifiable step) and turned into queued tasks
by `aion plan apply` (idempotent per `plan_id`). The cheap loop executes them.

## Apply order

| Order | Plan | Apply when | Steps (DET / A-B / D / C) |
|---|---|---|---|
| 1 | `plan-exp001-paid-consult.json` | now | 13 (6 / 4 / 3 / 0) |
| 2 | `plan-bridge-hardening.json` | now, in parallel | 6 (3 / 3 / 0 / 0) |
| 3 | `plan-t100-go-public.json` | **only after** `aion experiment EXP-001` says SUCCESS; its s1 gate fails until then | 9 (4 / 1 / 4 / 0) |

Zero class-C steps in any plan. Owner (D) steps become approval cards and
close by themselves once their `validation_command` passes (worker fix of
2026-09-05).

```bash
aion plan check incoming/plan-exp001-paid-consult.json
aion plan apply incoming/plan-exp001-paid-consult.json
aion work --max 10          # or let aion-work.timer / the daily routine do it
aion path                   # what is done, what is next, what needs the owner
```

Verified on 2026-09-05 in a fresh shared brain: all three plans pass
`plan check`; `plan apply` + `aion work` on plan 1 completed the DET steps,
raised the owner cards, and left the B steps waiting for a cloud worker with
their prompts intact.
