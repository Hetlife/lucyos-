# Canonical branch — 2026-09-17

**Canonical branch: `origin/main`**, frozen at commit `0720a920` ("owner: freeze
supervised integration candidate").

`main` carries all 23 S-task branches merged during the 2026-09-16/17 overnight
run. `integration/consolidation-20260916` is retained for history and for one
pending reconciliation: it is 8 commits ahead of that freeze point, carrying
owner commit `60b2dc7` ("feat: add local-first skill execution adapters") and
its four new `aion_core` modules, which have not yet reached `main`.

See `docs/internal/health-audit/HEALTH_REPORT.md` and
`docs/internal/health-audit/SONNET_EXECUTION_QUEUE.md` for the full audit and
the reconciliation plan (TASK-004).

Earlier planning documents (`.lucy/planning/INTEGRATION_ROADMAP_20260917.md`
and `INTEGRATION_ROADMAP_V2_20260917.md`, on branch
`planning/integration-roadmap-20260917`) describe
`integration/consolidation-20260916` as the target and `main` as the
destination. That is now inverted; those documents are superseded by this
file and by the health audit.

**Owner action still open:** `origin/HEAD` is unset on the remote, so a fresh
clone cannot infer the default branch from Git alone. Set it to `main`.
