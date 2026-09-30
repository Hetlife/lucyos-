# 08 — Master execution plan

Phases are dependency-ordered. Each work order is one file in `work_orders/`. Executors: DETERMINISTIC, LOCAL_MODEL, OPENCLAW, CLAUDE_CODE, CODEX, FABLE, OWNER. "Gate" = the level from `10_ACCEPTANCE_GATES.md` that closes the phase.

## Phase 0 — Reality reconciliation (entry: this package on `main`)
| ID | Title | Executor | Depends |
|---|---|---|---|
| TR-0-01 | Owner merges #88; adds override then merges #73; closes #2/#11; decides #53/#62 | OWNER (+FABLE for the override PR) | — |
| TR-0-02 | Planning hygiene: cherry-pick CODE_REVIEW, archive superseded plans, generate `.lucy/planning/INDEX.md` | DETERMINISTIC (+CLAUDE_CODE for the index script) | — |
| TR-0-03 | Authority re-freeze at the post-#73 SHA | FABLE + OWNER | TR-0-01 |
| TR-0-04 | Runtime census on Lucy-den, Mark-2, pad | CODEX | — |
| TR-0-05 | #73 override + CI re-run | FABLE + OWNER | — (verified: EV-PR73) |
| TR-0-06 | Tag every non-contained branch `archive/<name>`; produce delete script | CODEX (tags) + OWNER (delete) | — |
Exit: L1 items "authority ok" and "index current"; census JSON present. Rollback: none (docs, tags).

## Phase 1 — One reliable control plane
| TR-1-01 | CI: never cancel in-progress runs on `main` | FABLE + OWNER | — |
| TR-1-02 | Boundary ratchet to 0 warnings | CLAUDE_CODE | — |
| TR-1-03 | Governed `whatsapp` verb over OpenClaw (`lucyosctl` + forced-command dispatcher, identity, redaction, events) | CLAUDE_CODE | — |
| TR-1-04 | Bridge unit restart policy (override needed) | CLAUDE_CODE (+FABLE override) | D-5 |
| TR-1-05 | Live E2E: OpenClaw -> `status`, `approve` on Lucy-den | OPENCLAW + OWNER | TR-1-03 merged |
Exit: **L2 OPERABLE** proven live. Rollback: revert the bridge PR; OpenClaw falls back to read verbs.

## Phase 2 — Boring, reproducible runtime
| TR-2-01 | `scripts/clean_machine_proof.sh`: install -> verify -> export -> import -> verify | CLAUDE_CODE | — |
| TR-2-02 | Drive bridge configurable remote; nightly encrypted backup push | CLAUDE_CODE | — |
| TR-2-03 | Restore drill on Mark-2 from a Lucy-den archive | CODEX | TR-2-02 |
| TR-2-04 | Remove `/root` and machine-specific defaults; portability rule | CLAUDE_CODE (+FABLE override for `check_portability.py`, `systemd/**`) | — |
| TR-2-05 | Cost-per-verified-task metric in `aion usage` | LOCAL_MODEL draft + CLAUDE_CODE review | — |
Exit: L1 fully green incl. off-host backup evidence. Rollback: per-PR revert.

## Phase 3 — Real interfaces
| TR-3-01 | WhatsApp via OpenClaw live: channel linked, `status`/`approve` round trip from the phone | OWNER + OPENCLAW | TR-1-05 |
| TR-3-02 | LucyNest authority decision recorded (D-4) | OWNER + FABLE | — |
| TR-3-03 | Merge `devices/little_lucy` as inactive source (no TS package) | CLAUDE_CODE | D-4 |
| TR-3-04 | Archive SCG/RPAB design docs into `docs/architecture/`; re-verify empty-session churn fix | CLAUDE_CODE | — |
Exit: owner uses WhatsApp daily; LucyNest shows live status. Rollback: pad stays on its external runtime.

## Phase 4 — Executor routing
| TR-4-01 | Install Ollama on the primary host | OWNER | — |
| TR-4-02 | Executor registry + portable worker scripts (claude-code, codex, ollama) | CLAUDE_CODE (+FABLE override: `agents.py`, `worker.py`) | TR-0-04 |
| TR-4-03 | Context compiler in the worker (#73) verified live on one B task | CODEX | TR-0-05 |
| TR-4-04 | Routing report shows cost per verified task per executor | DETERMINISTIC | TR-2-05 |
Exit: **L3 AUTONOMOUSLY USEFUL**: a PLAN of 3 steps (DET, A, B) runs end to end, survives a kill, resumes, records evidence. Rollback: disable executors in `agents`.

## Phase 5 — Project / company / app productisation
| TR-5-01 | Ratify `06_` schema and overrides in the baseline | FABLE + OWNER | — |
| TR-5-02 | Migration v13: `workspaces`, `projects`, `project_integrations`; `aion workspace|project` commands; definitions in `COMPANIES/`, `PROJECTS/` | CLAUDE_CODE | TR-5-01 |
| TR-5-03 | Project scoping in tasks/memory/context/finance + `--project` everywhere | CLAUDE_CODE | TR-5-02 |
| TR-5-04 | Integration manifest kind + `aion integration install|enable|disable|revoke` | CLAUDE_CODE | TR-5-02 |
| TR-5-05 | SEVAA as the first integration manifest | CLAUDE_CODE | TR-5-04 |
| TR-5-06 | Project policy in router/governor/worker | CLAUDE_CODE (+override) | TR-5-02 |
| TR-5-07 | Scoped secrets resolver | CLAUDE_CODE | TR-5-02 |
Exit: **L4** (new project without core edits) then **L5** (company with 2 projects, 1 integration, scoped secret). Rollback: tables are additive; feature-flag `projects_enabled` in meta.

## Phase 6 — Deployment + clean-machine proof
| TR-6-01 | Mark-2 DC-1 deploy at the named SHA | CODEX | TR-0-03 |
| TR-6-02 | Clean-machine proof on a fresh Mark-2 user | CODEX | TR-2-01 |
| TR-6-03 | Cherry-pick `verify_installed_services.py` | CLAUDE_CODE | — |
| TR-6-04 | `scripts/update.sh` with verify + rollback | CLAUDE_CODE | TR-6-03 |
Exit: update+rollback demonstrated on Mark-2. Rollback: contract §7.

## Phase 7 — Mac-ready release
| TR-7-01 | launchd `aion-work` periodic | CLAUDE_CODE (+override `deploy/**`) | — |
| TR-7-02 | Mac runbook executed on the mini (steps 3–9 of `07_`) | OWNER + CODEX | phases 2, 4, 6 |
| TR-7-03 | Promotion + demotion + reboot test | CODEX + OWNER | TR-7-02 |
Exit: **L6 MAC PRODUCTION READY**. Rollback: Lucy-den resumes as primary.

## Phase 8 — First value-producing workload
| TR-8-01 | Set `SEVAA_AUTOMATION_TOKEN`; run `aion sevaa-reconcile` | OWNER | — |
| TR-8-02 | Nightly reconcile + daily brief in maintenance; `money` reflects it | CLAUDE_CODE | TR-8-01 |
| TR-8-03 | OpenClaw morning `status`/`money` push + approval handling routine | OPENCLAW | TR-3-01 |
| TR-8-04 | Second workload (strategy-factory project) created through the phase-5 path | OWNER + CLAUDE_CODE | phase 5 |
Exit: **L7** measured for 14 consecutive days. Rollback: disable the schedule.

## Critical path
TR-0-04 (census) -> TR-1-03 (write verb) -> TR-1-05 (live E2E) -> TR-3-01 (phone) -> TR-4-02 (executors) -> TR-5-02..06 (projects) -> TR-8-02 (value). Everything else runs in parallel lanes.

## Fable resume point (for the next Fable session)
1. Verify TR-0-03/TR-0-05 landed (`verify_authority.py self` ok; #73 merged). 2. Review TR-1-03 PR diff for identity/redaction. 3. Ratify TR-5-01 overrides. 4. Do not implement; assign.
