# LucyOS Total Recovery — read me first

**Author:** Fable (architecture/verification authority), 2026-09-30.
**Baseline:** first pass `origin/main` @ `36c954c` (795 tests); second pass (post-merge, same day) `origin/main` @ `fad9ed4` (#73 + #88 merged; 810 tests OK). See `13_CURRENT_REALITY_POSTMERGE.md`.
**Status of this package:** CURRENT. It supersedes every earlier plan under `.lucy/planning/`, `.lucy/execution/` and `docs/internal/` as the routing document. Those files stay as history and evidence; none of them is the task list any more.

## Mission (unchanged)
LucyOS is the control layer for Het's companies, projects, agents, machines, approvals, knowledge and automation. Owner steers from WhatsApp / LucyNest; the machine holds canonical state; work routes to the cheapest reliable executor; every result carries evidence; state survives restarts; new projects and companies plug in without editing the core.

**Resuming? Read `CHECKPOINT.md` first.** It records the exact state, what is in flight and the next steps as of 2026-09-30.

## Truth hierarchy used here
1. Live runtime + canonical SQLite (not reachable from this session: Lucy-den, Mark-2, Nebula are **UNKNOWN until TR-0-04 runs**).
2. Current code and Git objects at `36c954c` (verified directly).
3. Tests and CI (run locally: 795 OK; GitHub run #376 green).
4. PR/branch/commit history (all 88 PRs and 127 remote branches classified, see `03_`).
5. Checkpoints/ADRs/evidence in-repo (`.lucy/**`, `docs/internal/**`).
6. Drive (`MARK2_SHARED`, `LUCYOS_BACKUP`, planning folders): read for history only.
7. Old prompts/chats: not used as truth.

## How to use this package
| You are | Read | Then |
|---|---|---|
| Owner | `12_OWNER_SUMMARY.md` | make the listed decisions, run owner-only commands |
| Codex (Lane A) | `09_AGENT_ROUTING.md` §A, then the work orders tagged `CODEX` | one work order per session |
| Claude Code (Lane B) | `09_AGENT_ROUTING.md` §B, `10_ACCEPTANCE_GATES.md`, then one `CLAUDE_CODE` work order | one branch `task/<ID>-<slug>`, one PR, stop |
| OpenClaw (Lane C) | `09_AGENT_ROUTING.md` §C, work orders tagged `OPENCLAW` | operate, report, never redesign |
| Any agent, first 2 minutes | `evidence/EVIDENCE_INDEX.md` | do not re-derive what is indexed |
| Fable (next session) | `08_MASTER_EXECUTION_PLAN.md` §"Fable resume point" | verify milestones, do not implement |

## Files
```
00_READ_ME_FIRST.md            this file
01_SYSTEM_MAP.md               verified edges: interface -> authority -> AION -> executors -> evidence
02_CAPABILITY_MATRIX.md        status per capability, with proof and blockers
03_BRANCH_PR_LEDGER.md         every branch and PR classified; integration strategy
04_ERROR_REGISTER.md           ISSUE-* with root cause, real fix, executor
05_TARGET_ARCHITECTURE.md      what stays, what changes, what is rejected
06_PROJECT_COMPANY_APP_MODEL.md  workspace/project/integration contract
07_DEPLOYMENT_MAC_MIGRATION.md canonical roles now; Mac mini migration
08_MASTER_EXECUTION_PLAN.md    phases 0-8, dependency order, exit gates
09_AGENT_ROUTING.md            who does what; token rules
10_ACCEPTANCE_GATES.md         L1-L7 "running" levels, measurable
11_RISKS_AND_DECISIONS.md      decisions taken, decisions owed by the owner
12_OWNER_SUMMARY.md            plain-language state and next steps
13_CURRENT_REALITY_POSTMERGE.md  second-pass measurements (post-merge)
14_CLEANUP_REGISTER.md         dead/duplicate/obsolete items with proof and action
15_AI_OS_HARNESS_AUDIT.md      harnesses A-O: status, gap, work order
16_INTERFACE_ARCHITECTURE.md   Control Center, LucyNest, OpenClaw/WhatsApp roles
17_CRITICAL_PATH.md            dependency graph and level gates
18_AUDIT_20261004.md           whole-program audit 2026-10-04 (state, gates, issues 045-048, PR #2)
19_SONNET_PLAN.md              roles, waves, session loop and prompts for finishing with Sonnet
evidence/                      indexed evidence, generated ledgers
work_orders/                   TR-<phase>-<nn>.md, one executable task each
```

## Rules that bind every executor (unchanged from `.lucy/authority/`)
Never weaken/skip a test; never edit constitutional paths (`.lucy/authority/**`, `scripts/verify_authority.py`, `.github/workflows/lucyos-ci.yml`) except through a Fable-authored PR the owner merges; never invent a task ID; never push to `main`; no third-party dependency in core; no new `aion_core` module without a baseline entry; never print or store a secret; report what actually ran.

## Mapping from the post-merge master prompt's file names
| Prompt name | Here |
|---|---|
| 00_CURRENT_REALITY | `13_CURRENT_REALITY_POSTMERGE.md` (+ `evidence/EVIDENCE_INDEX.md`) |
| 01_SYSTEM_MAP | `01_SYSTEM_MAP.md` |
| 02_CAPABILITY_MATRIX | `02_CAPABILITY_MATRIX.md` |
| 03_ERROR_AND_MISTAKE_REGISTER | `04_ERROR_REGISTER.md` |
| 04_CLEANUP_REGISTER | `14_CLEANUP_REGISTER.md` |
| 05_AI_OS_HARNESS_AUDIT | `15_AI_OS_HARNESS_AUDIT.md` |
| 06_TARGET_ARCHITECTURE | `05_TARGET_ARCHITECTURE.md` |
| 07_PROJECT_COMPANY_APP_MODEL | `06_PROJECT_COMPANY_APP_MODEL.md` |
| 08_INTERFACE_ARCHITECTURE | `16_INTERFACE_ARCHITECTURE.md` |
| 09_DEPLOYMENT_MAC_PLAN | `07_DEPLOYMENT_MAC_MIGRATION.md` |
| 10_CRITICAL_PATH | `17_CRITICAL_PATH.md` (+ `08_MASTER_EXECUTION_PLAN.md`) |
| 11_MODEL_ROUTING | `09_AGENT_ROUTING.md` |
| 12_ACCEPTANCE_GATES | `10_ACCEPTANCE_GATES.md` |
| 13_RISKS_DECISIONS | `11_RISKS_AND_DECISIONS.md` |
| 14_OWNER_SUMMARY | `12_OWNER_SUMMARY.md` |
| work_orders/ | `work_orders/` (index in `work_orders/INDEX.md`) |
