# FABLE COMPLETION CRITERIA — PHASE 1 (OFFLINE)

You have no machine this session. Nothing here asks you to run anything, and
claiming you ran something is the one unrecoverable failure.

The session is DONE when all of these hold:

1. **EXPERIMENT.md** exists in full: one offer, one channel, one buyer type; a
   hypothesis stated so it can be false; unit economics with every cost named
   including model spend; the minimum valid test; a cost ceiling in INR; a time
   window; success and failure conditions **both as numbers**; and the decision
   each outcome forces.
2. Every number you could not determine is written `UNKNOWN` with the cheapest
   named way to learn it — not guessed, not averaged, not illustrated.
3. **MILESTONE_LADDER.md** names which rung is the real wall and why, and says
   where real capital must enter and roughly how much.
4. Each **plan-<name>.json** validates against PLAN_FORMAT.md: every step has a
   `validation_command` or `success_criteria`, DET steps have `exec_command`,
   A/B steps have `prompt`, and `depends_on` forms an acyclic graph.
5. No step is class C unless a weaker model genuinely cannot do it. Every C step
   you leave behind is money the owner spends again later.
6. A **HANDOFF** section states: what you assumed, what you could not determine,
   what the on-machine session should do first, and your honest estimate of what
   this session cost.

Anything not meeting its criterion is PARTIAL or UNKNOWN — never DONE. An
artifact that cannot fail a test is not finished, it is decoration.
