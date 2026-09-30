# 03 — Branch and PR ledger

Generated evidence: `evidence/branch_ledger_20260930.tsv` (from `scripts/branch_ledger.py --base origin/main`, 127 branches). Re-run the script instead of editing this table by hand. Correction to `docs/internal/BRANCH_DELETION_LIST_20260930.md` and PR #88: **8** branches have no merge base (not 6), and several "contained" S-task branches are actually re-landed with edits (patch-id differs). Nothing here deletes anything.

## Classes
| Class | Count | Meaning | Action |
|---|---|---|---|
| CONTAINED | 54 | every commit is an ancestor of `main` | delete (owner runs TR-0-06 script) |
| PATCH_IN_BASE | 7 | commits not ancestors but every patch is in `main` | record tip SHA, delete |
| UNRELATED | 8 | no merge base (pre-2026-09-13 history) | tag `archive/<name>` then delete; 3 carry salvage value (below) |
| UNIQUE | 58 | at least one patch absent from `main` | classified individually below |

## UNIQUE branches, classified
| Verdict | Branches | Why | Action |
|---|---|---|---|
| **INTEGRATION CANDIDATE** | `task/M-CONTEXT-02-worker-integration-20260925-rebased` (#73) | context compiler, 808 tests OK on today's main, anti-dup ok, strict fails only for the missing FABLE-10 override (EV-PR73) | TR-0-05: Fable adds override, owner merges |
| **INTEGRATION CANDIDATE (docs)** | `docs/stale-cleanup-20260930` (#88) | corrects stale docs; docs only | owner merges; TR-0-02 then supersedes |
| **CHERRY-PICK** | `candidate/deployment-preflight-rendered-units-20260918` (`scripts/verify_installed_services.py`), `review/code-review-20260924` (`CODE_REVIEW_20260924.md`, dangling ref), `docs/opus-planning-brief-20260924` (5 planning docs: archive under `.lucy/archive/`) | small, self-contained, valuable | TR-0-02 / TR-6-03 |
| **EXTRACT (inactive source)** | `task/lucynest-source-reconciliation-20260925` (`devices/little_lucy/**`, 2 docs) | the running LucyNest client; must live in the repo | TR-3-03 after decision D-4; exclude `packages/lucy-nest-design-system` (TS app: separate repo) |
| **EXTRACT (design only)** | `integration/lucyos-autonomous-wave-20260919` and its 4 siblings (`repair/worker-empty-session-churn`, `design/remote-privileged-action-broker`, `diagnostic/ci-full-suite`, `repair/ci-context-origin-main`, `repair/scg-device-key-cli`) | SCG docs + RPAB design are worth keeping; `gateway.py` needs third-party deps and CI edits (D-6 rejects as-is); `worker: skip empty-session churn` (1 commit) is a small fix to re-verify | TR-3-04 copies the 5 docs to `docs/architecture/`; churn fix re-landed if still reproducible |
| **SUPERSEDED by main** | `fable/S-47-ratification-verified`, `task/S-47-verify-verified`, `task/S-48-boundary-ratchet-verified`, `task/S-49-hermetic-verified`, `task/S-44-module-manifests`, `task/S-45-context-module`, `task/S-41/42/43-*` (both dates), `research/codebase-reduction-20260918`, `claude/lucyos-health-audit-sonnet-repair-gfzowc`, `feature/autonomy-growth-20260923` (#54 closed), `repair/s48-current-main-20260922`, `task/R-04-live-owner-setup`, `task/R-05-*`, `task/R-06-*` (PROGRESS lines only), `docs/progress-postmerge-20260924`, `task/S-01/08/10/15/17/18/20/21/24/28-*`, `owner/start-here-model-router-20260917`, `owner/wave0-authority-reconcile-20260917`, `integration/consolidation-20260916` (1 temp doc), `trip-smoke-opencode-20260925`, `feature/little-lucy-nebula-prep-20260920` (older LucyNest + a 1.7 MB git bundle; superseded by the 09-25 branch) | content re-landed via PRs #42–#72 or only planning/progress text | tag `archive/`, delete after owner approval |
| **REJECT** | `feature/resource-governor` = `repair/resource-governor-hermetic-openclaw-20260917` (second governor package, 2.6k lines), `feature/unlazy-completion-20260924` (vendors third-party skill, new core module), `feature/taskcheck-mvp-20260922` (Cloudflare app + base64 zip), `feature/context-pack` (third context generation), `feature/lucy-taskcheck-20260922` (re-landed as #69–#71 minus `prompt_orders.py`) | violate stdlib/anti-dup invariants or duplicate main | tag, delete; decision D-7 |
| **OWNER DECISION** | `task/prompt-work-order-20260924` (#62 draft: prompt lifecycle in `.lucy/prompts/`), `research/uiux-stack-20260922` (#53 draft, docs), `task/orghealth-m1-20260926` (generalises LearnRepo health; touches `db.py` without override), `candidate/scs-admin01-handoff-20260918` (older SCS handoff; main has #45) | not wrong, not needed for the critical path | close #62/#53 unless the owner wants them; TR-5-x may revisit orghealth |

## UNRELATED (no merge base) — salvage table
| Branch | Salvage value | Action |
|---|---|---|
| `claude/aion-whatsapp-control-1seild` (#2) | `aion_core/phone.py` + `bridges/web/phone.html` (superseded by `web/` + `api.py`), `deploy/fable/*` prompts, `PROJECTS/sevaa-sales-os` early files, `systemd/aion-codex.*` | close #2; tag `archive/pr2-aion-whatsapp-control`; nothing to port |
| `claude/fable-deploy-setup-mc5nr6` | same set + `docs/SECURITY_REVIEW.md`, `docs/MILESTONE_LADDER.md`, `deploy/routines/*`, `incoming/plan-*.json` | tag; copy `docs/SECURITY_REVIEW.md` and the 3 plan JSONs to `.lucy/archive/` (TR-0-02) |
| `feature/lucyos-aion-handoff` | 17 early handoff files | tag only |
| `backup/pre-mark2-loop-v1.2-20260908`, `candidate/mark2-loop-v1.2-20260908`, `owner/wave0-portability-refinement-20260917`, `setup/ci-integration-sync-20260916`, `test/authority-gate-positive-20260916` (#11) | content re-landed in the 09-16/17 integration | tag; close #11 |

## PR ledger (88 PRs)
| Group | PRs | State |
|---|---|---|
| Merged into `main` or the integration branch | #1, #3, #12–#23, #25, #26, #28, #31, #32, #35–#40, #42–#49, #55, #57–#61, #63–#72, #74–#87 | done |
| Closed as contained/duplicate (owner, 2026-09-30) | #4–#10, #24, #27, #29, #30, #33, #34, #41, #50–#52, #54, #56 | done |
| Open | #2 (close), #11 (close), #53 (owner), #62 (owner), #73 (**merge after override**), #88 (**merge**) | TR-0-01 |

## Integration strategy (dependency-aware)
1. Merge #88 (docs), then #73 after TR-0-05 adds the `FABLE-10` override to the baseline (protected path: Fable PR, owner merges with bypass, then TR-0-03 re-freeze covers both).
2. Cherry-picks (TR-0-02, TR-6-03) are independent and small; one PR each.
3. LucyNest source (TR-3-03) waits for decision D-4; it adds no runtime behaviour, so it can merge before the decision as inactive source if the owner prefers.
4. Everything else is tagged `archive/<branch>` (TR-0-06, no approval needed for tags) and deleted only on the owner's word.
5. Functionality lost by deleting after tagging: none. Tags keep every object reachable.
