# 08 — Task Card Contract

Every executable task is one card. Cards live in `16_FIRST_10_TASKS.md` (initial set) and, from then on,
as `tasks/<TASK_ID>.md` in this folder; their graph entry lives in `06_TASK_GRAPH.json`. A card missing any
field is `NEW`, not `READY`.

**TASK_ID rule.** Must match `(S|FABLE|OWNER|CODEX)-\d{1,4}` — `scripts/verify_authority.py` derives task
identity from the branch name `task/<ID>-<slug>` or a `Task-ID: <ID>` trailer with exactly this regex. Any
other prefix silently disables the strict gate. Ranges reserved by this program: `S-40…S-59` (worker tasks),
`FABLE-05…FABLE-12`, `OWNER-06…OWNER-12`, `CODEX-01…` (Mark-2 deploy tasks only).

```
TASK_ID:                    S-4N
TITLE:                      imperative, ≤ 70 chars
MILESTONE:                  M0 … M9
OBJECTIVE:                  the end state, one sentence
WHY_THIS_EXISTS:            the measured problem it removes (cite evidence/ file or 01 row)
AUTHORITY_LEVEL:            L0 | L1 | L2 | L3 | L4 | L5   (04 §2)
OWNER/CONTROLLER:           ChatGPT/DEV (default) | Fable | Owner
EXECUTOR:                   controller | codex | claude-code | local-model | deterministic
INDEPENDENT_REVIEWER:       must differ from EXECUTOR for L2+; "ci+controller" allowed for L0/L1
CANONICAL_SHA:              origin/main SHA the card was written against
WORK_BRANCH:                research/codebase-reduction-20260918 | task/<ID>-<slug>
WORKTREE:                   detached worktree path convention on the node (never the node's live checkout)
PREREQUISITES:              task ids (must be DONE) + owner decisions (must be recorded)
RELEVANT_MODULE:            one of the 8 modules (02 §3) or "meta"
CONTEXT_PACK:               exact command(s) that produce the pack; budget in files and bytes
REQUIRED_LUCY_SKILLS:       smallest-fix (always for code) | learnrepo | code-review | none
LEARNREPO_NEEDED:           yes/no + why (external pattern that would save tokens/risk; or "no: internal")
ARCHITECTURE_AUDIT_REQUIRED: pre: <commands + checklist owner>  post: <commands>
FILES_ALLOWED:              exact paths/globs
FILES_FORBIDDEN:            exact paths (always includes every protected path unless an override is named)
STATE_TOUCHED:              none | <table/meta key> (any value other than none ⇒ L3+)
SUCCESS_CRITERIA:           objective PASS conditions, each checkable by a command or a diff
TARGETED_TESTS:             exact test modules/classes
REGRESSION_TESTS:           full suite + scan + portability + anti-dup + strict (+ boundaries from S-48)
SECURITY_CHECKS:            ./aion scan . ; no new network/subprocess/shell; no secret paths read
BEFORE_METRICS:             which 14 metrics, measured how, value
AFTER_METRICS:              same keys, filled at CHECKPOINT
ROLLBACK:                   git revert <merge> | close PR | delete files | tag pre/<ID>
MAX_ATTEMPTS:               3 (05 §4)
STOP_CONDITIONS:            explicit; always includes "needs a protected path", "needs a dependency",
                            "needs a public contract change", "start state drifted"
OWNER_APPROVAL_REQUIRED:    none | <decision id from 04 §5>
EVIDENCE_OUTPUT:            paths under evidence/ and/or the PR body
NEXT_TASKS_UNLOCKED:        task ids
```

## Commit and PR conventions (unchanged from the 2026-09-16 queue)

- Branch `task/<TASK_ID>-<slug>` from `origin/main` for code; docs/evidence commit directly on the research
  branch with `Task-ID:` trailer.
- Commit first line `<TASK_ID>: <what changed>`; trailer `Task-ID: <TASK_ID>`; one task per PR; never merge
  your own PR into `main`.
- PR body sections: Task · Base SHA · Files changed · Tests run + results · Gates (strict/anti-dup/
  portability/scan/boundaries) · Verifier report link · Metrics before/after · Known limitations · Rollback ·
  Owner/Fable action required.
- Worker result packet, verbatim field names: `STATUS / ACTIONS / FILES_CHANGED / TESTS / RESULTS /
  BLOCKERS / NEXT_ACTION` (`context.py` and `aion_codex_worker.sh` already require this).
