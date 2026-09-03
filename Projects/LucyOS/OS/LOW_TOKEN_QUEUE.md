# Low-Token / Local Task Queue

These are bounded tasks suitable for deterministic tools or a small local model.
Each task must write a short result and evidence path; no broad context is needed.

## Ready

- [ ] L1: List candidate SEVAA bundle and project paths; report filenames only.
- [ ] L2: Compare bundle SHA-256 with `AION_MANIFEST.json`; report pass/fail.
- [ ] L3: List archive top-level directories and suspicious secret-like filenames;
  do not open private-state files.
- [ ] L4: Read `CHECKPOINT.json`; extract `next_step`, `resume_command`, and
  `blocked_on` into a three-line handoff.
- [ ] L5: After verification output exists, summarise test counts and failures in
  five lines without interpreting architecture.
- [ ] L6: Build a changed-file list from hashes; skip unchanged files.

## Refusal boundary

Refuse architecture, security posture, spending, legal/compliance, credentials,
account ownership, public deployment, external outreach, destructive actions, or
any recommendation requiring judgement. Return exactly:

`CANNOT DO THIS — needs the main agent`

## Output format

```text
TASK: <ID>
RESULT: <one sentence>
EVIDENCE: <path or command>
NEXT: <one bounded next step or NONE>
```
