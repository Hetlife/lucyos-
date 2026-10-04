# Useful cleanup only
| Item | Evidence | Action / test / rollback |
|---|---|---|
| Four contract skeletons | #104 on main; test definitions now 813 vs 864 | DONE code archive; do not recreate or remove again; preserve archived rationale |
| Boundary warnings | #101; local scan zero | DONE code; reconcile stale INDEX |
| SCG/RPAB design files | #103 | design archive done; churn-code fix still separate |
| PR2 salvage record | #100; only #102 open | record done; independently verify archival tag and business bundles before deletion |
| 71 contained + 8 patch-equivalent live branches | branches-live.tsv | candidate archive only; verify tag/tip and owner deletion approval; keep dirty worktrees |
| Seven stale local tracking refs | live remote comparison | harmless; pruning optional, no need to block G2 on it |
| Historical ledgers/checkpoints | contradictory statuses and merge-base claim | add a current baseline pointer and precise delta overlay; never mass-delete evidence |
| Generated evidence directory | full test suite generated untracked evidence | explicitly stage only audit files; never git add -A |
| UI design-system/source overlap | two distinct LucyNest branch lines | compare native assets separately from TS package; do not merge inherited obsolete stack |
| Broad refactors/dependency removals | no concrete operation blocker shown | defer unless profile/repro proves value |
