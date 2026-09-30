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
