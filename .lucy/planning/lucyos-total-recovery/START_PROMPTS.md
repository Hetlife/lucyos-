# Start prompts (copy-paste), 2026-09-30

Until `fable/total-recovery-20260930` is merged, every prompt below begins with
`git fetch origin && git checkout fable/total-recovery-20260930`. After the merge, replace that with `git checkout main && git pull`.

## Codex — census (TR-0-04)
```
You are Codex, Lane A for LucyOS. Read only: .lucy/planning/lucyos-total-recovery/00_READ_ME_FIRST.md, evidence/EVIDENCE_INDEX.md, work_orders/TR-0-04.md. Do not read the rest of the repo.
Execute TR-0-04 exactly: read-only commands on Lucy-den, Mark-2 and the Nebula pad; write census_<host>_<date>.json and CENSUS_SUMMARY.md under .lucy/planning/lucyos-total-recovery/evidence/; never include secret values or phone numbers; run `./aion scan` on the evidence dir.
Open one PR from branch task/TR-0-04-runtime-census. Do not merge. Report: STATUS, ACTIONS, FILES_CHANGED, TESTS, EVIDENCE_KEYS_ADDED, BLOCKERS, NEXT.
```
Then TR-0-06 (tags + delete script) with the same header.

## Claude Code — first code work order (TR-1-03)
```
You are Claude Code, Lane B for LucyOS, on Lucy-den in a fresh worktree from origin/main.
Read only: START_HERE.md, .lucy/planning/lucyos-total-recovery/00_READ_ME_FIRST.md, 10_ACCEPTANCE_GATES.md, work_orders/TR-1-03.md, and the files that work order names.
Implement TR-1-03 exactly as scoped. Never edit router.py, approvals.py, anything under .lucy/authority/, scripts/verify_authority.py or .github/workflows/lucyos-ci.yml. No new aion_core module, no third-party dependency, no secret values anywhere.
Before pushing: full suite, ./aion scan ., scripts/check_portability.py, scripts/verify_authority.py strict --base origin/main --branch <b>, anti-dup, scripts/check_boundaries.py; report real exit codes.
Branch task/TR-1-03-openclaw-whatsapp-verb, one PR, stop. If the change needs a protected file, stop and report BLOCKED_HIGH_MODEL_DECISION with the path.
```
Queue after it (same header, swap the work order): TR-1-02, TR-1-06 (needs the override first), TR-2-02, TR-2-04 (needs override), TR-C-02, TR-I-01.

## OpenClaw — operations (until TR-1-03 merges, read verbs only)
```
Preflight: scripts/lucyosctl status; scripts/lucyosctl health. Morning: send the owner `status` and `blockers` output. Never run shell outside lucyosctl verbs, never store state, never spend money. When TR-1-03 is merged and pulled, approvals go through `scripts/lucyosctl whatsapp "approve <ID>"` with LUCYOS_PRINCIPAL set to the sender id; then execute work_orders/TR-1-05.md and record evidence.
```

## Fable — next session
```
Read .lucy/planning/lucyos-total-recovery/00_READ_ME_FIRST.md, 17_CRITICAL_PATH.md, evidence/EVIDENCE_INDEX.md and the census files if present. Verify TR-0-03/TR-1-01 landed; review the TR-1-03 PR diff for identity and redaction; record overrides for TR-1-06, TR-2-04, TR-4-02, TR-5-01 in the baseline; do not implement.
```
