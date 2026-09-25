# LucyOS branch rescue — first assessment (2026-09-21)

## Scope and safety

- Read-only archaeology only. No branch, ref, worktree, or commit was deleted or rewritten.
- A complete local Git bundle was created before classification.
- `main`, the integration stream, and Lucy-Nest remain separate responsibilities.

## Recovery evidence

- Bundle: `evidence/lucyos-all-refs-20260921.bundle`
- Bundle verification: PASS; 131 refs recorded and complete history reported by `git bundle verify`.
- SHA-256: `evidence/lucyos-all-refs-20260921.bundle.sha256`
- Ref manifest: `evidence/REF_MANIFEST.tsv`
- Branch census: `evidence/BRANCH_CENSUS.tsv`
- Patch-equivalence data: `evidence/PATCH_EQUIVALENCE.tsv`
- Integration gap: `evidence/INTEGRATION_GAP.tsv`
- PR reconciliation: unavailable because GitHub CLI authentication was unavailable; ordinary GitHub SSH transport is healthy.

## Current anchors

- Canonical `origin/main`: `05c4f0ddff7e01f1aaccf7a1c927730e6977766a`
- Integration: `55546fe82ddfba25e527df237766ae7c09346389`
- Lucy-Nest: `518b9970a7b5a9b1d5083cf61549684eab5d9b07`

## First classification

- 26 local branches and 87 remote-tracking refs were inventoried.
- 6 local branch tips are already contained in `origin/main`; 6 are contained in the integration stream.
- 13 local branch tips still have patch-unique commits relative to integration. They require task/PR/session mapping before any retirement decision.
- Lucy-Nest has 12 branch-unique patches relative to integration and remains an active product stream, not a consolidation target.
- Local-only security and supervisor branches are preserved. Their absence from a remote is not evidence that they are disposable.
- No retirement manifest or merge-wave plan is safe yet.

## Gap summary

- `main...integration`: main-only 18 commits; integration-only 41 commits.
- `main...Lucy-Nest`: main-only 18 commits; Lucy-Nest-only 23 commits.
- `integration...Lucy-Nest`: integration-only 30 commits; Lucy-Nest-only 12 commits.

## Next branch-rescue action

Map the 13 patch-unique local branches to LucyOS tasks, worktrees, sessions, and available remote/PR evidence; then classify each as active, integrated-equivalent, historical evidence, or merge candidate. No merges or retirements should occur before that map exists.
