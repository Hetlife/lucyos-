# bundles/

SEVAA-side work produced by a session that cannot push to
`het-life/sevaaconnect-realestate` (the git proxy scopes credentials per
session owner). Each `.bundle` is one task branch, built on `main` at
`a85a8cc`, with its own tests green and its commit message carrying full
validation evidence.

| Artifact | Branch/action | Task | Status |
|---|---|---|---|
| `S05-pointer-files.bundle` | `agent/coordinator/S05-pointer-files` | S05 | done, 36 passed |
| `S01-enquiry-notify.bundle` | `agent/sales/S01-enquiry-notify` | S01 (SEVAA side) | done, 45 passed |
| `S06-source-attribution.bundle` | `agent/sales/S06-source-attribution` | S06 | done, 40 passed |
| `S04-branch-hygiene.sh` | script, not a bundle | S04 | **prepared, not run** — needs push access to verify-then-delete/tag remote branches |

S07, S02 and S09 needed no SEVAA-side changes (the APIs they use already
existed) — see the AION repository's own commit history for those.

## Applying the bundles

```bash
cd sevaaconnect-realestate
for f in S05-pointer-files S01-enquiry-notify S06-source-attribution; do
  git fetch <path>/bundles/$f.bundle refs/heads/*:refs/heads/*
done
git push -u origin agent/coordinator/S05-pointer-files
git push -u origin agent/sales/S01-enquiry-notify
git push -u origin agent/sales/S06-source-attribution
```

Open PRs and merge in the order in `../AION_TASK_QUEUE.md`. S01's SEVAA-side
branch should land alongside the AION-side commit `0dc7888` on
`Hetlife/lucyos-` — the two halves are one contract.

## Running S04

Read `S04-branch-hygiene.sh` before running it — it re-verifies every tree
hash against the current `main` and refuses to proceed if `main` has moved
since 2026-09-04. It deletes seven confirmed-merged branches, tags and
deletes two deferred-Postgres branches, and deliberately leaves three
unmerged, non-deferred branches alone (see the script's own comments for
which and why — that split is a human decision, not something the script
makes for you).
