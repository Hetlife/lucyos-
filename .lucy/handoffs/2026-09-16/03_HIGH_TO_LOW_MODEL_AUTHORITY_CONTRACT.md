# LucyOS High-Model → Low-Model Authority Contract

## Purpose

LucyOS uses model capability hierarchically. Expensive/high-capability reasoning establishes architecture, authority boundaries, security policy and execution constraints. Lower-cost executors implement bounded tasks. Lower models do not get to silently redefine the problem they were asked to solve.

## Authority order

OWNER
→ FABLE / highest-capability architecture authority
→ OPUS / high-capability review and adversarial audit
→ SONNET / bounded coding executor
→ LOCAL MODELS / mechanical, offline or low-risk execution
→ DETERMINISTIC SOFTWARE / preferred for repeatable enforcement.

Execution should usually flow in the reverse direction of cost:
DETERMINISTIC → LOCAL → CHEAP CLOUD → SPECIALIST → HIGH-CAPABILITY → OWNER.

## High-model protected decisions

The following classes of decision are high-authority and may not be changed by Sonnet/local workers unless a new Fable/owner-approved task explicitly permits it:

- system architecture and control-plane boundaries;
- canonical state and persistence rules;
- approval and owner-authority policy;
- security and secrets policy;
- model-routing/escalation policy;
- resource-governor policy;
- merge/deployment policy;
- architecture anti-duplication rules;
- trusted recovery/backup policy;
- protected-path definitions;
- CI gates that enforce this contract;
- the frozen Fable execution package itself.

## Executor rights

A lower-cost executor MAY:

- implement a task exactly as specified;
- edit only allowed files/paths;
- add tests required by the task;
- run deterministic checks;
- report failures and unexpected evidence;
- create task-scoped commits/branches;
- improve local implementation details when they do not alter architecture or task scope.

A lower-cost executor MUST NOT:

- re-plan the system;
- broaden scope;
- replace AION or introduce a parallel control plane;
- add duplicate schedulers, databases, memories, approval systems, governors or agent frameworks;
- weaken validation because a task is inconvenient;
- modify protected high-model files;
- weaken or bypass CI/security/approval gates;
- change repository visibility or credentials;
- merge into main;
- deploy a floating branch;
- make real financial, legal or trading commitments;
- hide a deviation by calling it a refactor.

## Required escalation

If implementation cannot satisfy the task without violating a protected decision, the worker must:

1. stop the affected task;
2. preserve partial work separately;
3. record the exact evidence and conflicting constraint;
4. mark the task `BLOCKED_HIGH_MODEL_DECISION` or equivalent;
5. propose options, not silently choose one;
6. return to Fable/owner for a new decision.

Unrelated safe tasks may continue.

## Deterministic freeze

Before Sonnet begins bulk coding, Fable should create:

- `.lucy/authority/HIGH_MODEL_BASELINE.json`
- `.lucy/authority/PROTECTED_PATHS.md`
- an exact `FABLE_FREEZE_SHA`
- protected path/hash or baseline references
- a deterministic CI verifier.

The preferred verifier compares the executor branch against files at the exact `FABLE_FREEZE_SHA`. This avoids trusting a manifest that a lower model could modify. The verifier, the authority manifest, and the workflow invoking it are themselves protected.

## Commit / task traceability

Every lower-model code change should map to a task ID. A Sonnet commit should be reviewable as:

`TASK-ID: concise implementation description`

The cumulative Sonnet diff must be reviewable against the frozen task queue and high-model baseline before deployment.

## Double verification

Consequential implementation is not accepted from a model claim alone.

Preferred acceptance:

1. clean CI verification from a fresh checkout; and
2. later Mark-2 deployment/rehearsal verification against the exact reviewed SHA.

For local model or generative output, independent deterministic validation is preferred before marking work complete.

## Merge and deployment

- No lower model merges into `main`.
- Fable reviews the integration candidate first.
- Codex/Mark-2 deploys an exact reviewed SHA, with snapshot and rollback.
- Main/canonical merge remains owner-gated.

## Principle

**Lower-cost models are executors, not constitutional authorities. High-capability work should leave behind durable contracts, tests and machine-enforced boundaries so cheaper workers can make progress without being allowed to silently change the reasoning that defined the work.**
