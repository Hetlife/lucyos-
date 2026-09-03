# LucyOS Model Handoff Protocol

Purpose: allow work to continue safely when the active AI model reaches a limit,
is downgraded, or is replaced.

## Source of truth

The files in this directory are authoritative. Hidden chat memory is not required.
Never place passwords, API keys, OTPs, recovery codes, private keys, or private_state
in these files.

## Model lanes

### Lane A — High-capability planner

Use for architecture, ambiguity, adversarial review, major decisions, and detailed
task decomposition.

Writes:
- `HIGH_MODEL_PLAN.md`
- `CHECKPOINT.json`
- `LOW_TOKEN_QUEUE.md`
- `APPROVALS_REQUIRED.md`

### Lane B — Normal execution model

Use for integrating plans, bounded implementation, verification, and reporting.
Reads only the relevant task packet and checkpoint. Updates the checkpoint after
each meaningful step.

### Lane C — Small/local model

Use for deterministic classification, extraction, file finding, summarisation,
tagging, duplicate detection, and other low-risk chores.

Rules:
- receive a narrow task packet, not the whole repository;
- use local exact search before model inference;
- return the requested format exactly;
- never make architectural, financial, legal, security, credential, or irreversible
  decisions;
- if judgement is needed, return:
  `CANNOT DO THIS — needs the main agent`.

### Lane D — Deterministic tools

Use first for manifests, hashes, tests, status checks, parsing, filtering, and
reconciliation. These tasks consume no model tokens.

## Handoff sequence

1. Read `CHECKPOINT.json` and `RESUME.md`.
2. Read only the active task packet.
3. Confirm the checkpoint revision and task ID.
4. Execute one bounded step.
5. Run the listed verification command.
6. Write result, evidence, errors, and next step to the checkpoint.
7. Update `RESUME.md` with the exact next command or action.
8. Move completed work out of the active queue.

## Token policy

- Plan once, then execute from the plan.
- Fingerprint inputs and skip unchanged work.
- Prefer exact local search and deterministic scripts.
- Send compact evidence packs to larger models.
- Use a high-capability model only for uncertainty or high-value judgement.
- Do not reread a full repository for routine cycles.
- Do not run duplicate schedulers or duplicate workers.

## Approval policy

The model lane never changes the approval boundary. Spending, public publishing,
credential/account ownership, security weakening, destructive actions, legal
commitments, and consequential external communication remain approval-gated.
