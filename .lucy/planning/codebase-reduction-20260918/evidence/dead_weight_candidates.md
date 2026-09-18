# Dead-weight candidates report (S-42)

Advisory evidence from `scripts/duplication_scan.py`. Reports only; nothing was deleted or modified by generating this file.

## Dead-weight module candidates

A module is listed only when all four checks below are negative -- any single reference (an importer, CLI wiring, a test, or a manifest/doc mention) excludes it.

- `scripts/authorize_drive.py` — [no importers] [no CLI wiring] [no test import] [no manifest/.lucy/docs reference]

## Dead links

Checked 7 relative markdown link targets repo-wide for `[text](path)` links that resolve to nothing on disk.

None found.

## Superseded planning docs

Self-declared (a `# SUPERSEDED` heading), or listed by the task card in `KNOWN_STALE_PLANNING_DOCS` for cases the generic heuristics cannot derive on their own.

- `.lucy/planning/CANONICAL_BRANCH.md`
  - task-card ground truth: Named origin/main frozen at 0720a920 as canonical; overtaken by later owner freezes (e.g. 'owner: freeze reconciled governance baseline', 'owner: freeze governed MSOS candidate') with no update recorded here.
- `.lucy/planning/INTEGRATION_ROADMAP_20260917.md`
  - task-card ground truth: Roadmap V1 names integration/consolidation-20260916 as target and main as destination; inverted once main was frozen as the candidate.
- `.lucy/planning/INTEGRATION_ROADMAP_V2_20260917.md`
  - self-declared SUPERSEDED heading
  - task-card ground truth: Roadmap V2; self-declares superseded at its own tail (also caught generically).
- `.lucy/planning/OPUS_ROADMAP_REVISION_PROMPT_20260917.md`
  - task-card ground truth: One-shot planning prompt for the V2 revision pass; the pass it requested is done and its own inputs (roadmap V1, integration branch as ground truth) are stale.
