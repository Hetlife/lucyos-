# 21 — Reality audit delta, 2026-11-14 (Fable)

A delta on `18_`/`20_`, not a new plan. Baseline `main` @ `316e33e`. Raw data: `evidence/baseline_20261114.json`, `evidence/branch_ledger_20261114.tsv`, `evidence/unique_branch_value_20261114.csv`, `evidence/e2e_loop_20261114.txt`. Everything here was run in a cloud sandbox on the Git repository. **Lucy-den, Mark-2, the live AION DB, OpenClaw, WhatsApp, LucyNest and Drive were not reachable and are UNVERIFIED in this audit.**

## 1. What is true now
| Area | State | Evidence |
|---|---|---|
| Code health on main | 843 tests OK; portability, secret scan, boundaries, anti-dup pass | local run, baseline JSON |
| CI on main | **RED since 2026-11-07** (8 pushes). One cause: `ubuntu-latest` is 26.04, which has no Python 3.9 | run 42386407490 (ISSUE-049) |
| Authority gate | TR-* overrides were **dead letters**: verifier id pattern only knew S/FABLE/OWNER/CODEX, so PR #115 fails "task id undeclared" | job 128445794376 (ISSUE-050) |
| Authority drift | 6 files, unchanged; re-freeze still owed (TR-0-03) | `verify_authority.py self` |
| Governed loop, DET class | TESTED: clean install → task → worker → validation → evidence → DONE → backup/restore → reboot keeps state | `e2e_loop_20261114.txt` |
| Approval grammar | TESTED: loose text decides nothing; exact `APPROVE <ID>` decides | same file |
| Loop on a real host, model classes A/B/C, OpenClaw attribution | NOT PROVEN (Stage A1–A3 of `20_` still open) | no access |
| Company/project entity | ABSENT: `project` is a text column; no tables (TR-5-02) | schema probe |
| macOS | CI_PASS only (`macos-readiness` green, advisory). Worker plist runs once at load, no interval (TR-7-01) | CI, `deploy/launchd` |
| Dependencies | stdlib only; no lockfile needed today | import scan |

## 2. Branch reconciliation (133 branches, 3 open PRs)
74 CONTAINED + 8 PATCH_IN_BASE = **82 need nothing but tag-and-delete** (TR-0-06, owner-run). 51 UNIQUE, decided per row in the CSV:

| Class | n | Decision |
|---|---|---|
| UNIQUE_VALUABLE | 3 | `task/TR-1-06…` (#115), `task/TR-AGENT-HARNESS…` (#111), `task/fix-codex-worker-portable-20261102` (PR opened today). All three merged with this branch in a throwaway worktree: **897 tests OK, all gates pass** |
| PARTIAL_VALUABLE | 9 | no stack merges. SCG wave (6 branches, one patch family): only the churn fix mattered and #115 re-implements it. LucyNest native source (`devices/little_lucy`, ~98 files absent from main, 2 branches): extract only after comparing with the deployed device (TR-3-03, needs Lucy-den). Legacy snapshots (2): business bundles only, TR-C-05 |
| SUPERSEDED | 32 | verdict inherited from `final-merge-20261004` (tips unchanged) plus #109, which main already contains as `a6b9fd4` → close |
| UNKNOWN_NEEDS_REVIEW | 7 | FM-06 bounded review; none is on the critical path |

Nothing was merged to main, deleted or force-pushed.

## 3. Blockers by root cause
| ID | P | Root cause | Fix | State |
|---|---|---|---|---|
| ISSUE-049 | P0 | CI image lost Python 3.9 | pin the 3.9 leg to `ubuntu-24.04` | fixed on this branch; owner merge (constitutional file) |
| ISSUE-050 | P0 | verifier cannot match TR-* ids | pattern accepts `TR-<x>-<nn>`; two tests written failing first | fixed on this branch; owner merge |
| ISSUE-047/TR-0-03 | P1 | 6-file authority drift, freeze SHA stale | re-freeze after #115 | queued (Fable) |
| Stage A | P1 | no live proof on Lucy-den since 2026-10-01 | A1–A3 of `20_` | owner/Codex, blocked on access |
| EV-PROJECT | P1 | no company/project entity | TR-5-01 → TR-5-02 | queued |

## 4. Mac path
One codebase, stdlib Python, SQLite, launchd units and a macOS adapter already exist, and the suite passes on GitHub's Apple Silicon runner. That is compatibility evidence, not a live Mac. Open items: TR-7-01 (periodic worker), the `/root` paths removed by the portable-worker branch, clean-machine proof (TR-2-01), off-host backup and restore drill (TR-2-02/03), then TR-7-02 on the real machine.
RAM (estimates, to be measured on the machine): LucyOS itself needs well under 1 GB; RAM only decides local-model routing. 24 GB: one small/medium local model at a time for class-A work, everything else to cloud. 48 GB: a larger local model or two concurrent, fewer cloud calls. Neither blocks installation. Single-writer rule after promotion is unchanged from `07_`: Mac primary, Lucy-den standby with the DB read-only until a fenced failover.

## 5. Gates (mapping to the owner's G0–G9)
G0 baseline: **met for code/CI**, unverified for hosts. G1 canonical repo: after TR-R-01. G2 engineering health: after TR-R-01 + TR-0-03 + TR-2-02/03. G3 operable from phone: Stage A3. G4 verified loop: DET proven in sandbox; needs A2 live, then TR-4-02/4-05. G5: TR-5-02…. G6: TR-I-01/02. G7: TR-7-01 + TR-2-01. G8: TR-7-02. G9: TR-8-*.
**First unblocked gate: G1.** Exit evidence: main CI green on all 6 required checks; `branch_ledger.py` shows 0 UNIQUE_VALUABLE unmerged; `verify_authority.py self` = 0 drift.

## 6. First execution batch
| # | Order | Executor | Outcome | Depends |
|---|---|---|---|---|
| 1 | TR-R-01 step 1 | OWNER (admin merge) | this branch on main; CI green; TR overrides usable | none |
| 2 | TR-R-01 steps 2–4 | OWNER + Fable review of #111 | #115, portable-worker PR, #111 merged with green CI; #109 closed | 1 |
| 3 | TR-0-03 | FABLE | re-freeze: authority drift 0 | 2 |
| 4 | TR-7-01 | CLAUDE_CODE | worker plist runs every 600 s; test asserts it | 1 |
| 5 | Stage A1–A3 (`20_` §2) | OWNER or CODEX on Lucy-den | live task DONE with evidence; probe 3; `decided_by` attribution | 2 |
Then: TR-0-06 (delete 82 merged branches), TR-5-01/5-02.

## 7. Owner decisions
Merge the Fable PR with admin bypass (it edits two constitutional files, by design). Close #109. D-11 (branch deletion) and D-14 (Mac timing, 24 vs 48 GB) remain open from `11_`.
