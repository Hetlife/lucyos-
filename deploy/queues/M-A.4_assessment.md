# M-A.4 Assessment — experiments.py / money_path.py cherry-pick

Method: attempted a real `git cherry-pick -n` of the source commit (`45403ba`,
branch `claude/fable-deploy-setup-mc5nr6`) onto `origin/main` in an isolated
worktree; when that produced unrelated conflicts, isolated the two target
files specifically with `git checkout <branch> -- <path>` and ran their real
test files against `main`. No change was made to `main`; the worktree was
discarded after the assessment.

## Whole-commit cherry-pick: fails, but not because of these two files

`45403ba` bundles the two new modules together with SEVAA/phone-interface/docs
work that no longer exists on `main` in the same shape. 10 files conflict:
`aion_core/cli.py`, `aion_core/reports.py`, `bridges/whatsapp_bridge.py`,
`docs/OPERATIONS.md`, `tests/test_bridge.py` (content conflicts — both sides
changed the same lines), plus `aion_core/phone.py`, `bridges/web/phone.html`,
`PROJECTS/REGISTRY.md`, `deploy/fable/README.md`, `docs/MASTER_BRIEFING.md`
(delete/modify — `main` removed these files entirely when it replaced the old
phone interface with `bridges/http_server.py` + `web/`).

## The two target files in isolation: apply cleanly

`aion_core/experiments.py` and `aion_core/money_path.py` themselves import
only `db`, `util`, `bootstrap`, `milestones` — all present and unchanged on
`main`. Checked out alone (no whole-commit pick), both land with zero
conflicts (`git status` showed clean `A` adds, nothing else touched).

## The actual conflict surface: their tests, not their logic

`tests/test_experiments.py` and `tests/test_money_path.py` both do:
```python
from aion_core import experiments, metrics, phone, reports
...
dash = phone.dashboard()
```
`aion_core.phone` does not exist on `main` — that responsibility moved to
`bridges/http_server.py`, which reads structured data rather than exposing a
`phone` module `import`able from `aion_core`. Confirmed by direct import
attempt: `ImportError: cannot import name 'phone' from 'aion_core'`.

Everything else the tests touch (`metrics`, `reports`) exists on `main`
unchanged in the relevant surface.

## Overlap with main's own finance/delivery work

None found. `money_path.py`'s job (an ordered, owner-facing "steps to real
money" checklist per project, DONE/NEXT/LATER from deterministic checks) does
not duplicate `main`'s `deliveries.py`/`payer_id` work (evidence-gated
delivery records feeding `finance`) — they operate at different layers and
could compose: `money_path` as a narrative wrapper over the same underlying
evidence `deliveries.py` already produces.

## Recommendation: ADAPT

Not MERGE (the whole commit doesn't apply and shouldn't — it would resurrect
a deleted interface). Not DROP (the two modules' actual logic is sound,
tested in their original context, and duplicates nothing on `main`).

Concretely, a follow-up task (not this one — this task is assessment-only):
1. Cherry-pick only `aion_core/experiments.py` and `aion_core/money_path.py`
   as new files (clean, shown above).
2. Port `tests/test_experiments.py` and `tests/test_money_path.py`, replacing
   the two `phone.dashboard()` assertions with the equivalent check against
   `aion_core/api.py`'s `system_snapshot()`/`money_split()` (M-A.1, already on
   this branch) — same intent (prove the card/step data surfaces), correct
   interface.
3. Wire `PROJECTS/<project>/money_path.json` reads into `api.projects()` as an
   optional enrichment, not a new endpoint — avoids growing the route surface
   for one feature.

Estimated size: one bounded task, same shape as M-A.1/M-A.2, no architecture
decision required beyond what this assessment already settled.
