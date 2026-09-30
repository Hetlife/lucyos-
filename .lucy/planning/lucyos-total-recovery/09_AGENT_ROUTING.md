# 09 — Agent routing and token rules

## Lanes
| Lane | Executor | Does | Never does | Context it gets |
|---|---|---|---|---|
| A | **CODEX** (Drive + Mark-2 + Lucy-den + GitHub) | cross-machine census, deploys at exact SHA, restore drills, tags/branch scripts, live E2E evidence, multi-tool debugging | deterministic edits a script could do; architecture changes; merges | the work order + `evidence/EVIDENCE_INDEX.md` + the contract it executes |
| B | **CLAUDE_CODE** (Lucy-den worktrees) | bounded code: one task, named files, tests, one PR | "fix LucyOS"; new core modules; protected paths without a recorded override; merges | the work order + `START_HERE.md` + the files it names |
| C | **OPENCLAW + WHATSAPP** (Lucy-den) | owner tasks/approvals/status, health checks, scheduled routines, `work-dry`, small DET runs | canonical state writes outside `aion`; secrets; design | `integrations/openclaw/lucyos/SKILL.md` + the routine |
| D | **DETERMINISTIC** | `branch_ledger.py`, `planning_index.py`, `check_*`, `unittest`, `sync-docs` | — | none |
| L | **LOCAL_MODEL** (Ollama) | docstrings, test scaffolds, table reformatting, summaries of logs; reviewed by lane B before commit | commits | the file it edits |
| F | **FABLE** | architecture, reconciliation, security reasoning, overrides/freeze, acceptance, milestone review | mechanical work; implementing features | this package |
| O | **OWNER** | merges, secrets, money, tunnels, hardware, decisions in `11_` | — | `12_OWNER_SUMMARY.md` |

## Routing rules
1. Prefer D > L > C > B > A > F for any step that the lower lane can verify with a test or a script.
2. A work order names exactly one executor; a second executor appears only as "review" or "verify".
3. Fable reviews: protected-path changes, identity/authority/secret handling, schema changes, anything marked `Fable review: YES`.
4. Nobody re-derives what `evidence/EVIDENCE_INDEX.md` already states; cite the key. Refresh a key only with a new observation.
5. Every work order result is a packet: `STATUS, ACTIONS, FILES_CHANGED, TESTS (real output), EVIDENCE_KEYS_ADDED, BLOCKERS, NEXT`. Record executor, wall time, estimated tokens/cost, retries in the PR description or census file.
6. One branch per work order (`task/TR-x-nn-<slug>`), one PR, never merge.

## Token economics
- Context packets: `aion context <TASK_ID>` (already bounded) is the input for lane B/L; do not paste the repo.
- Indexes before prose: `EVIDENCE_INDEX.md`, `branch_ledger_*.tsv`, module manifests, `INDEX.md` (TR-0-02).
- Scripts before judgement: ledger, boundaries, portability, tests. If a script can answer, no model is asked.
- Cached evidence: census JSON (TR-0-04) is reused by every phase-1/2 work order.
- Target metric (TR-2-05/TR-4-04): tokens and INR per **verified** DONE task, per executor, reported by `aion usage`.

## Executor ladder per task type (post-merge addendum)
| Task type | First choice | Escalate to | Never |
|---|---|---|---|
| scans, indexes, ledgers, gates, formatting, health | DETERMINISTIC (scripts) | — | any model |
| docstrings, test scaffolds, table reformats, log summaries, classification of low-risk items | LOCAL_MODEL (Ollama, class A) | CLAUDE_CODE review | Fable |
| status, approvals, notifications, morning routine, `work --dry-run`, small DET runs on the primary host | OPENCLAW (DET verbs) | owner | design decisions |
| bounded code with named files and tests; schema migrations under an override; UI read models | CLAUDE_CODE (class B) | FABLE review for protected/identity/schema | merges |
| cross-machine census, deploys, restore drills, Drive, tags, multi-tool debugging, Mac runbook | CODEX | FABLE review of evidence | canonical state edits outside `aion` |
| architecture, contradictions, security/authority, overrides, freeze, acceptance, prioritisation | FABLE | owner | mechanical edits |
Rule of thumb: if a script or test can decide it, no model is asked; if one model can verify it, a second model is not asked; a frontier model reads a work order and the evidence index, never the repo.
