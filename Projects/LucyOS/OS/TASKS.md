# LucyOS OS Tasks

## Intake

- [x] Collect the remaining AION handoff files.
- [ ] Verify the referenced SEVAA deployment bundle before using it.
- [x] Verify the referenced SEVAA deployment bundle before using it.
- [x] Map AION components to LucyOS workers and permissions.
- [x] Define deterministic-first routing and local-model limits.
- [x] Define recovery/resume state and checkpoint format.
- [ ] Add security and QA gates before any deployment.

## Model handoff system

- [x] Add high-model planning packet and low-token task queue.
- [x] Add revisioned checkpoint and resume card.
- [x] Add explicit approval register and small-model refusal boundary.
- [ ] Restore and locally verify SEVAA from the supplied bundle.

## Rules

- Keep OS architecture and project goals in separate files.
- Preserve incoming source files unchanged.
- Never store passwords, API keys, tokens, or private keys in this layer.
- Do not deploy, publish, or push without explicit approval.

## Manifest status

- Received and recorded `AION_MANIFEST.json` and `AION_STATE.md`.
- Still required for hash-verified intake: AION_BOOT_PROMPT.txt,
  AION_MACHINE_AGENT_PROMPT.txt, AION_SETUP_AGENT_GUIDE.txt, AION_TASK_QUEUE.md,
  state/AION_MACHINE_STATE.json, and the SEVAA deployment ZIP.
- Verify every received item against the manifest before using or deploying it.
- AION task queue received and stored as `AION_TASK_QUEUE.md`.
