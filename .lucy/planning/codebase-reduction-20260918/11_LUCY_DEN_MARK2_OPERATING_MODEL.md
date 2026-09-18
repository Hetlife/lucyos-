# 11 — Lucy-den ↔ Mark-2 Authority and Execution Design

## 1. Roles (owner policy, confirmed consistent with code)

| | Mark-2 | Lucy-den |
|---|---|---|
| Canonical AION state (`$AION_HOME/state/aion.sqlite3`) | **owns** | never (a local `AION_HOME` there is disposable, like a test's) |
| Task queue / scheduler | **owns**: `aion-work.timer` (10 min) → `build_loop.sh` → `aion boot` + `aion work --max 10`; nightly `maintenance.sh` | none for runtime; dev tasks live in git (05 §1) |
| Always-on monitoring / heartbeat / health | **owns** (`aion health`, `ci_health_gate.py` semantics) | not a monitor |
| Safe cloud workers | Codex class-B worker via `scripts/aion_codex_worker.sh` (when configured with `set-cloud-cmd`) | Codex/Claude Code sessions for *development* |
| External APIs / bridges | WhatsApp bridge, HTTP interface, Drive bridge (reads live, writes broken per FABLE_PROGRESS) | none in production |
| Development worktrees, local models, deterministic analysis, review | — | **owns** |
| Deploy | receives an exact SHA per `MARK2_DEPLOYMENT_CONTRACT.md`, executed by Codex-with-Mark-2-access | never deploys |

## 2. The divergence that must be resolved first (OWNER-06)

Both nodes run `feature/resource-governor` @ `2cd3cc5` (owner Drive baseline, 2026-09-18). `main` is
136 commits ahead and lacks: `aion verify`, hermetic test env, `resource_governor/`, `research_registry`.
`main` has, and the nodes lack: waves 1–5 (S-23/S-26/S-27/S-29/S-30, openclaw bridge, four owner modules,
authority allowlist fixes, `derived_sqlite_allowed`).

Consequences today: (a) `HIGH_MODEL_BASELINE.json` on `main` already allowlists `resource_governor`,
`research_registry`, `bridge` — pre-provisioned for S-03, so salvage will not trip anti-dup; (b) any
"Mark-2 evidence" describes `2cd3cc5` behaviour, not `main`; (c) DC-1 is unnamed, so **no deploy is
currently authorised** by the contract — the nodes' checkout predates the contract's freeze.

Options for the owner (exactly two, per 04 §5):
- **(a) Name DC-1 = `66e3a4e`** (or its successor after S-47/S-49 land): Codex-on-Mark-2 runs the contract
  §1–§8; Lucy-den re-clones `main`. The resource governor returns to `main` later via S-03/S-04 under Fable
  cards. Cheapest path to "measurements describe the running code".
- **(b) Keep `2cd3cc5` on the nodes** and fast-track S-03/S-04 (resource governor salvage, L3, owner merges),
  then name DC-1 at that SHA. Preserves whatever the governor is doing on Mark-2 today; costs one L3 merge
  first.

The program never touches the nodes' checkouts itself. Until OWNER-06, every measurement is taken in a
**detached worktree of `origin/main`** on Lucy-den (the Drive baseline already states this rule).

## 3. How work moves between nodes without split brain

```
GitHub main  ──(owner merge)──►  is the only source of code for both nodes
     ▲                                   │
     │ PRs from task branches            │ deploy = exact SHA in MARK2_DEPLOYMENT_CONTRACT.md
     │                                   ▼
Lucy-den ──► development, packs, tests, review          Mark-2 ──► runs the loop on canonical state
     │                                                        ▲
     └── results that Mark-2 must *know about* travel as ──────┘
         AI SYNC PACKETs (`aion ingest`, packets.py: idempotent by hash; TASKS/APPROVALS sections
         become rows; secrets refused) or as Drive files promoted through sync_outbox (C2).
```

Rules:
1. Lucy-den never writes Mark-2's SQLite. If a dev result must become a Mark-2 task (e.g. "install
   `aion verify` into the nightly maintenance"), it is a packet or a PR, and Mark-2 ingests it on its own
   `aion boot` (`packets.ingest_inbox()`), or the owner runs `aion task-add`.
2. Mark-2 never runs research-branch code. Only a contract-named SHA.
3. The controller (ChatGPT/DEV) reads Mark-2 evidence only from committed/sanitised sources: the Drive
   baseline doc, `aion health`/`aion status` output the owner pastes, or a future `aion verify` report
   committed under `evidence/` by the owner. It does not infer Mark-2 state from its absence in the repo.
4. Cross-node packets carry the 7-field result packet; `worker._validate` semantics are untouched.
5. A future node (Mac, per C1) joins by the same three seams: `main` SHA in, packets in/out, contract deploy.

## 4. What Lucy-den must not become

- a second canonical queue: dev tasks are git rows, not AION rows that Mark-2 would race with;
- a monitor of Mark-2: health is Mark-2's own; Lucy-den reads reports;
- a deployer: no `systemctl`, no `git checkout` on Mark-2 from Lucy-den sessions;
- a place where secrets live for the program: the program needs none (git + GitHub + Drive read).

## 5. What Mark-2 must not become

- a place where planning happens: `.lucy/planning/**` is excluded from every pack the Mark-2 worker gets;
- a second architecture authority: `architecture.py`/`verify_authority.py` are the same on both nodes by
  construction (same SHA);
- silently divergent from `main`: OWNER-06 closes this, and M9 entry criterion (5) keeps it closed.

## 6. Knowledge layers (master prompt §20) — what belongs where

| Layer | Holds | Never holds |
|---|---|---|
| GitHub (`main` + branches) | code, tests, authority contracts, module manifests, this planning package, `evidence/*.md` measurements | secrets, private logs, customer data, Mark-2 DB dumps |
| Google Drive `LucyOS/Architecture_Research/Codebase_Reduction_2026-09/Fable_Execution_Architecture/` | human-readable mirror of this package, gate reports, owner decisions, pilot results | anything not also in git (Drive is a copy, never the only copy) |
| Mark-2 `$AION_HOME` | canonical state, RESUME.md, sessions, backups | planning text, research branches |
| Lucy-den | worktrees, local `AION_HOME` scratch, model caches | canonical anything |

Duplication rule: a document is authored once, in git; Drive receives an export at each milestone gate
(22). Owner decisions made in Drive comments are transcribed into `CHECKPOINT.md` by the controller with
the Drive link as provenance.
