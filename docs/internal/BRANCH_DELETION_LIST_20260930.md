> STATUS: HISTORICAL — superseded by `.lucy/planning/lucyos-total-recovery/` (Fable, 2026-09-30). Evidence, not instructions.

# Branch deletion list (prepared, NOT executed): 2026-09-30

> **CORRECTION (2026-09-30, later the same day).** The first version of this file listed six branches as "zero file
> differences" and safe to delete once the tip SHA was recorded. **That was wrong.** Those branches have *no merge base*
> with `main` (unrelated histories), so the three-dot `git diff` used to classify them errored silently and printed
> nothing, which read as "0 files". Compared properly they differ from `main` in 393 to 487 files each, and at least three of them hold
> files `main` lacks (17 to 51 each). They are now section D and must **not** be deleted. Groups A and B are unaffected: A is decided by
> "is the tip an ancestor of `main`", B by `git cherry`, and neither can fail this way.

**Nothing has been deleted.** Deleting a branch is an owner action. This is the evidence to decide with.
Computed against `origin/main` @ `cda8059`. Remote branches (excluding `main`): **126**.

| Group | Count | Meaning |
|---|---|---|
| A. Contained in `main` | 65 | Every commit is already in `main`. Deleting loses nothing. |
| B. Patches already in `main` under different commit IDs | 7 | Every commit's exact patch is already in `main` (`git cherry`). **Record the tip SHA before deleting.** |
| D. Unrelated history, **KEEP** | 6 | No merge base with `main`. They hold real work `main` does not have (section D). An earlier version of this file wrongly listed them as zero-difference. |
| C. Unique work, keep | 48 | At least one commit's patch is not in `main`. Do not delete without a decision. |

**Open PRs.** Deleting a branch that has an open PR closes that PR (as happened to #76 and #77). The `PR` column shows which.
Two group-C branches with open PRs are judged superseded by inspection (noted below); they are the reason the master plan lists 19 PRs to close.

## A. Contained in `main`: safe to delete (65)
| Branch | Tip | Open PR |
|---|---|---|
| `audit/health-20260917` | `85b330c` |  |
| `candidate/dev-msos-20260917` | `a99beeb` |  |
| `candidate/dev-msos-governed-20260918` | `66e3a4e` |  |
| `feature/learnrepo-queue-health` | `75459ad` |  |
| `feature/lucy-nest-live-status-20260923` | `42b1a11` |  |
| `feature/openclaw-lucyos-bridge` | `dd08043` |  |
| `feature/skill-system-q000-architecture-audit` | `67e5ebb` | #4 |
| `feature/skill-system-q001-capability-registry` | `8ed208a` | #5 |
| `feature/skill-system-q002-manifest-schema` | `88452a1` | #6 |
| `feature/skill-system-q003-catalog-lifecycle` | `e7eb615` | #7 |
| `feature/skill-system-q004-learnrepo-contract` | `47f1236` | #8 |
| `feature/skill-system-q005-policy-classes` | `ba42b2f` | #9 |
| `feature/skill-system-q006-architecture-guard` | `2b59aea` | #10 |
| `fix/context-shallow-origin-main-20260925` | `e058d14` |  |
| `integrate/taskcheck-het-20260923` | `20143bd` |  |
| `merge/reconcile-waves-20260917-chatgpt` | `a99beeb` |  |
| `mission/sonnet-repair-20260923` | `b6b4d51` |  |
| `owner/dev-msos-governance-20260918` | `d59a76e` |  |
| `owner/start-here-model-router-20260917` | `effd0e6` |  |
| `owner/wave0-authority-reconcile-20260917` | `1430af2` |  |
| `owner/wave0-portability-refinement-20260917` | `b3f129c` |  |
| `planning/integration-roadmap-20260917` | `13f3510` |  |
| `planning/opus-fable-20260916` | `c11fcb6` |  |
| `post-integration/S-30-result-contract` | `f6487d1` |  |
| `repair/bridge-canonical-path-20260919` | `1ca0c46` |  |
| `repair/mark2-user-systemd-20260923` | `d88fad9` |  |
| `repair/orchestration-reliability-20260919` | `00567ee` |  |
| `repair/reconcile-20260917` | `0ed33e7` |  |
| `repair/scs-handoff-reconcile-20260919` | `d1a6ec2` |  |
| `review/R-07-final-candidate-20260924` | `e8cc58d` |  |
| `setup/ci-integration-sync-20260916` | `6a5f7d8` |  |
| `supervised/integration-20260917` | `0720a92` |  |
| `task/R-01-execution-contract` | `66676e8` |  |
| `task/R-01-owner-setup-real-command` | `e2cb7ed` |  |
| `task/R-02-owner-setup-bridge-vars` | `6bb5cc0` |  |
| `task/R-03-authority-aware-health` | `7fa5aa0` |  |
| `task/S-01-skill-registry-normalize` | `9b4e947` |  |
| `task/S-02-salvage-audit-branch` | `da780bd` | #34 |
| `task/S-05-launchd-units` | `4c37a27` |  |
| `task/S-07-drive-check` | `6f02f08` |  |
| `task/S-08-secret-scanner-kwarg` | `3131c9d` |  |
| `task/S-09-openclaw-check` | `24cd78a` | #27 |
| `task/S-10-host-adapter` | `612f5ef` |  |
| `task/S-13-sync-outbox` | `1f28fd4` |  |
| `task/S-14-intake` | `c1831eb` |  |
| `task/S-15-openclaw-independence` | `57e1488` |  |
| `task/S-16-tempworker-guardrails` | `dc0d88b` |  |
| `task/S-17-guardian-skeleton` | `a939d34` |  |
| `task/S-18-recovery-injection` | `13fb8cf` |  |
| `task/S-19-macos-read-safe` | `d06b199` |  |
| `task/S-20-protected-paths-render` | `4b2fc56` |  |
| `task/S-21-history-scan` | `81153b7` |  |
| `task/S-22-remove-desktop-commander` | `ab7f8e4` |  |
| `task/S-23-portability-export` | `08406e3` | #24 |
| `task/S-24-encrypted-backup` | `1f65121` |  |
| `task/S-26-audit-chain` | `c34b56f` | #29 |
| `task/S-27-routing-report` | `4226001` | #30 |
| `task/S-28-runtime-inventory` | `b34a482` |  |
| `task/S-29-salvage-experiments` | `6510ec9` | #33 |
| `task/S-44-module-manifests-20260925` | `b40b747` |  |
| `task/S-45-context-module-20260925` | `ea1c2c1` |  |
| `task/S-47-aion-verify` | `d99ac49` |  |
| `task/S-49-hermetic-tests` | `ed65416` |  |
| `task/cerebras-e0-cost-safety-20260925` | `79a8aaa` |  |
| `task/eaa-token-scanner-20260927` | `4467aca` |  |

## D. Unrelated history: KEEP (6)
No merge base with `main`, so `git merge-base` finds nothing and a three-dot diff errors. Counts are a plain two-dot tree comparison with `main`.
"Only on branch" = files present on the branch that `main` does not have.

| Branch | Tip | Commits | Files differing from main | Only on branch |
|---|---|---|---|---|
| `arch/lucyos-interface-m-a` | `fab1506` | 36 | 393 | 2 |
| `backup/pre-mark2-loop-v1.2-20260908` | `e126529` | 12 | 424 | 0 |
| `candidate/mark2-loop-v1.2-20260908` | `2c12556` | 13 | 425 | 1 |
| `claude/aion-whatsapp-control-1seild` | `a968606` | 35 | 470 | 39 |
| `claude/fable-deploy-setup-mc5nr6` | `cc778c9` | 39 | 471 | 51 |
| `feature/lucyos-aion-handoff` | `0afe7d7` | 2 | 487 | 17 |

Example: `claude/aion-whatsapp-control-1seild` (PR #2) has 39 files `main` lacks, including `aion_core/phone.py`, the `deploy/fable/` set and the Sevaa Sales OS project files.
Three of the six (`claude/aion-whatsapp-control-1seild`, `claude/fable-deploy-setup-mc5nr6`, `feature/lucyos-aion-handoff`) have
17 to 51 files `main` lacks: real work. The other three (`arch/...`, `backup/...`, `candidate/...`) have 0 to 2 such files; their
hundreds of differences are mostly *older versions* of files `main` has since changed, so they are probably superseded backups.
That is still not "identical", so keep all six until the owner decides.

## B. Every patch already in `main` under a different commit ID (7): delete only with the SHA recorded
| Branch | Tip (KEEP THIS) | Commits ahead | Files differing | Open PR |
|---|---|---|---|---|
| `candidate/learnrepo-sse-study-20260918` | `13d31a2` | 1 | 1 |  |
| `fix/ci-informational-drift-20260923` | `c28c020` | 1 | 1 |  |
| `plan/lucyos-openclaw-e2e` | `5ab467c` | 1 | 1 |  |
| `repair/cerebras-e0-20260922` | `75859ef` | 1 | 2 | #50 |
| `repair/mac-resolver-20260922` | `e40197d` | 1 | 3 | #51 |
| `repair/taskcheck-required-owner-value-20260923` | `392f755` | 1 | 4 | #56 |
| `review/autonomy-growth-main-20260923` | `13939ee` | 2 | 6 |  |

## C. Unique work: keep (48)
"Patches not in main" counts commits whose exact patch is missing from `main`; it can over-count work that was re-landed
with edits (see the Note column).
| Branch | Tip | Commits ahead | Files differing | Patches not in main | Open PR | Note |
|---|---|---|---|---|---|---|
| `candidate/deployment-preflight-rendered-units-20260918` | `c542bd9` | 1 | 3 | 1 |  |  |
| `candidate/scs-admin01-handoff-20260918` | `61f86a3` | 2 | 4 | 1 |  |  |
| `claude/lucyos-architecture-audit-4o4q83` | `b501403` | 2 | 3 | 2 |  |  |
| `claude/lucyos-health-audit-sonnet-repair-gfzowc` | `332d3a7` | 4 | 26 | 3 |  |  |
| `design/remote-privileged-action-broker-20260920` | `a43d09d` | 37 | 77 | 35 |  |  |
| `diagnostic/ci-full-suite-20260920` | `e8ae894` | 37 | 76 | 35 |  |  |
| `docs/opus-planning-brief-20260924` | `16bef89` | 4 | 5 | 4 |  |  |
| `docs/progress-postmerge-20260924` | `a5e1db6` | 1 | 1 | 1 |  |  |
| `fable/S-47-ratification-verified` | `735f3dd` | 14 | 53 | 13 |  |  |
| `feature/autonomy-growth-20260923` | `a751741` | 1 | 6 | 1 | #54 | main has the newer version (d6df8c4) |
| `feature/context-pack` | `73d7f51` | 2 | 4 | 1 |  |  |
| `feature/little-lucy-nebula-prep-20260920` | `301ec61` | 28 | 106 | 27 |  |  |
| `feature/lucy-taskcheck-20260922` | `64be2a9` | 23 | 40 | 19 |  |  |
| `feature/resource-governor` | `6daa15c` | 4 | 34 | 4 |  |  |
| `feature/taskcheck-mvp-20260922` | `0c3280a` | 5 | 4 | 5 |  |  |
| `feature/unlazy-completion-20260924` | `5f302a9` | 1 | 35 | 1 |  |  |
| `integration/consolidation-20260916` | `a3cf46b` | 2 | 1 | 2 |  |  |
| `integration/lucyos-autonomous-wave-20260919` | `55546fe` | 41 | 77 | 37 |  |  |
| `plan/R-followups-20260930` | `911f525` | 6 | 5 | 5 | #82 |  |
| `repair/ci-context-origin-main-20260920` | `bbf99dc` | 37 | 76 | 35 |  |  |
| `repair/resource-governor-hermetic-openclaw-20260917` | `6daa15c` | 4 | 34 | 4 |  |  |
| `repair/s48-current-main-20260922` | `47826b8` | 1 | 2 | 1 | #52 | files byte-identical to main (via #68) |
| `repair/scg-device-key-cli-20260920` | `3dae4c1` | 35 | 76 | 34 |  |  |
| `repair/worker-empty-session-churn-20260920` | `71c8324` | 41 | 79 | 37 |  |  |
| `research/codebase-reduction-20260918` | `1dbda69` | 11 | 46 | 10 |  |  |
| `research/uiux-stack-20260922` | `39e72df` | 1 | 6 | 1 | #53 |  |
| `review/code-review-20260924` | `32891d2` | 1 | 1 | 1 |  |  |
| `task/M-CONTEXT-02-worker-integration-20260925` | `77363bf` | 5 | 8 | 5 |  |  |
| `task/M-CONTEXT-02-worker-integration-20260925-rebased` | `7a1ac8a` | 5 | 8 | 5 | #73 |  |
| `task/R-04-live-owner-setup` | `12fe05e` | 2 | 5 | 1 |  |  |
| `task/R-05-openclaw-aion-proof-20260924` | `e246e7e` | 1 | 1 | 1 |  |  |
| `task/R-06-unattended-reliability-proof-20260924` | `7f7e03d` | 1 | 1 | 1 |  |  |
| `task/S-41-complexity-map` | `88f9e4f` | 1 | 5 | 1 |  |  |
| `task/S-41-complexity-map-20260925` | `606a47d` | 1 | 2 | 1 |  |  |
| `task/S-42-duplication-scan` | `90a8eae` | 1 | 4 | 1 |  |  |
| `task/S-42-duplication-scan-20260925` | `d3f349e` | 1 | 2 | 1 |  |  |
| `task/S-43-context-profiler` | `1166a03` | 1 | 3 | 1 |  |  |
| `task/S-43-context-profiler-20260925` | `d78eefc` | 1 | 2 | 1 |  |  |
| `task/S-44-module-manifests` | `4a2d281` | 8 | 43 | 8 |  |  |
| `task/S-45-context-module` | `c623517` | 2 | 14 | 1 |  |  |
| `task/S-47-verify-verified` | `907c083` | 12 | 49 | 11 |  |  |
| `task/S-48-boundary-ratchet-verified` | `6ee5a12` | 15 | 56 | 14 |  |  |
| `task/S-49-hermetic-verified` | `b1b011d` | 12 | 48 | 11 |  |  |
| `task/lucynest-source-reconciliation-20260925` | `32bc916` | 36 | 110 | 35 |  |  |
| `task/orghealth-m1-20260926` | `4a80348` | 1 | 6 | 1 |  |  |
| `task/prompt-work-order-20260924` | `8b18347` | 2 | 5 | 2 | #62 |  |
| `test/authority-gate-positive-20260916` | `34ffcea` | 1 | 1 | 1 | #11 |  |
| `trip-smoke-opencode-20260925` | `986b35c` | 28 | 96 | 27 |  |  |

## Deleting group A (the Claude session cannot: the git proxy returns HTTP 403 on branch deletes)
On 2026-09-30 the owner approved deleting group A. All 65 were re-proved as contained in `main` @ `36c954c`, but the
deletion itself is **blocked in the Claude session**: every `git push --delete` returned HTTP 403, and no GitHub tool
offers a delete-branch call. So it is a two-step job for the owner, from any machine with the repo:
```bash
git fetch origin --prune
awk '/^## A\./{f=1;next} /^## D\./{f=0} f' docs/internal/BRANCH_DELETION_LIST_20260930.md \
  | grep -oE '^\| `[^`]+`' | sed 's/^| `//; s/`$//' > /tmp/group_a.txt
wc -l /tmp/group_a.txt                      # expect 65
# 1) dry run: read every line, expect only SAFE
while read b; do git merge-base --is-ancestor "origin/$b" origin/main && echo "SAFE $b" || echo "STOP $b"; done < /tmp/group_a.txt
# 2) delete, but only branches that still prove contained (a STOP line is skipped, never deleted)
while read b; do git merge-base --is-ancestor "origin/$b" origin/main && git push origin --delete "$b"; done < /tmp/group_a.txt
```
Or use the branches page on GitHub. Deleting a branch that still has an open PR closes that PR.

## Re-prove before you delete anything
This is a snapshot; `main` moves. Run this immediately before deleting, and delete only lines that print `SAFE`.
```bash
git fetch origin --prune
for b in $(cat branches_to_delete.txt); do
  if git merge-base --is-ancestor "origin/$b" origin/main; then echo "SAFE(contained) $b"
  elif [ "$(git diff --name-only origin/main...origin/$b | wc -l)" = "0" ] \
    || [ -z "$(git cherry origin/main origin/$b | grep '^+')" ]; then
       echo "SAFE(content in main; record tip $(git rev-parse --short origin/$b)) $b"
  else echo "STOP $b has unique work"; fi
done
```
Never delete `main`. Never delete a group-C or group-D branch without a decision. A deleted branch is easy to recreate while you still
have its tip: `git push origin <tip>:refs/heads/<branch>`.

## Notes
- `task/R-01-owner-setup-real-command` and `task/R-02-owner-setup-bridge-vars` were **recreated on 2026-09-30** to reopen #76
  and #77 after GitHub closed them. They are contained in `main`.
- Closing the 19 obsolete PRs is a separate decision: `.lucy/execution/SONNET_MASTER_PLAN_20260930.md` section 3.

