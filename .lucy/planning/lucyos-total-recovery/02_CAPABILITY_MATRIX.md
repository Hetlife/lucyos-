# 02 — Capability matrix

Columns: status | implementation | tests | live proof | blockers | dependencies | target | priority. Status vocabulary as in `01_`. "Live proof" is what has been *observed*, not what code implies. Evidence keys refer to `evidence/EVIDENCE_INDEX.md`.

| Capability | Status | Implementation | Tests | Live proof | Blockers | Dependencies | Target | Priority |
|---|---|---|---|---|---|---|---|---|
| Bootstrap / config | CI_VERIFIED | `scripts/install.sh`, `bootstrap.py`, `config.py` (AION_HOME, caps) | `clean-bootstrap-health` job, `test_seed`, `test_hermetic` | EV-RUNNABILITY (clean clone) | root-path defaults in units/scripts (ISSUE-016) | — | idempotent on Linux+macOS, no root assumptions | P1 |
| Canonical DB / migrations | CI_VERIFIED | `db.py` 31 tables, schema v12, additive `_migrate` | `test_migrations`, `upgrade-from-main-schema` job | EV-CI | — | — | + `workspaces`, `projects`, `project_integrations` (v13) | P2 (phase 5) |
| AION control plane (CLI, router, reports) | CI_VERIFIED | `cli.py` ~80 cmds, `router.py`, `reports.py`, `api.py` | `test_router`, `test_api`, `test_end_to_end` | EV-RUNNABILITY | — | — | keep | — |
| Tasks / sessions / checkpoints / crash recovery | CI_VERIFIED | `tasks.py`, `sessions.py`, `resume.py`, `errors.py` | `test_task_reliability`, `test_recovery_injection`, `test_notebook_sessions` | R-02 (Mark-2, secondhand) | — | — | keep | — |
| Leases / concurrency | TESTED | `worker._execution_lock` singleton, `tasks.claim`, `release_stale` (45 min), learnrepo leases | `test_plan_worker`, `test_learnrepo` | — | single-machine lock only | — | fine for one primary host | — |
| Approvals / authority / governor | CI_VERIFIED | `approvals.py`, `router` strict verbs, `governor.py`, `metrics.budget_status` | `test_approvals`, `test_routing_and_state` | none live via phone | no governed approve verb via OpenClaw (G-A) | E2 | approve/deny reachable from OpenClaw+WhatsApp with identity | **P0** |
| Planner -> executor / model routing / local routing | TESTED | `plan.py`, `agents.route`, `worker._do_work`, `model_gateway` (free aux providers), Ollama, one cloud cmd | `test_plan_worker`, `test_model_gateway` | no executor configured anywhere observed | Ollama not installed; cloud cmd unset; single global cmd | owner installs Ollama | named executors per class (claude-code, codex, ollama) + per-project policy | P1 |
| OpenClaw integration | PARTIAL | skill + `lucyosctl` + SSH forced-command dispatcher; `openclaw-check` | `test_openclaw_lucyos_bridge`, `test_openclaw_check` | `reachable` on Lucy-den (secondhand) | read-only; `/root` defaults | — | governed command envelope incl. `whatsapp` verb | **P0** |
| WhatsApp (direct Meta) | IMPLEMENTED | `whatsapp_bridge.py cloud`, `bridge_preflight.py`, runbook | `test_bridge*` | never reached a phone | 6 vars, public tunnel, owner choice | — | optional; keep dormant | P3 |
| SCG / device trust | DESIGNED (+branch impl) | branch `integration/lucyos-autonomous-wave-20260919` | branch tests | none | 3 third-party deps, CI edit, stdlib invariant | decision D-6 | redesign later as stdlib HMAC device tokens inside the OpenClaw envelope | P3 |
| LucyNest (pad + PWA + supervisor) | PARTIAL / LIVE (secondhand) | main: `web/` PWA, `health.supervisor_*`; branch: `devices/little_lucy/*` | `test_supervisor`, `test_http_v1`; branch tests | pad live on LAN, touch broken | authority decision D-4; source not on main | — | pad = read-only status until D-4; source merged inactive | P2 |
| Memory / context / recall | CI_VERIFIED | `memory.py` FTS, `context.py`, `recall/lexical`, optional `semantic_recall` | `test_context_contract`, `test_semantic_recall` | — | no project scoping; #73 unmerged | #73 | project-scoped context compiler | P1 |
| Project / company isolation | ABSENT | `project` text column only (EV-PROJECT) | — | — | schema, CLI, policy absent | phase 5 | `06_` model | P1 (phase 5) |
| Knowledge | PARTIAL | memory kinds + `learnrepo/references` + `PROJECTS/<id>/` files | `test_learnrepo` | — | no per-project knowledge roots | phase 5 | project knowledge roots indexed by recall | P2 |
| Skills / registry / LearnRepo / Fable pack | CI_VERIFIED | `skills.py`, `skills/manifest.schema.json`, catalog (empty), `learnrepo.py`, `fable.py` pack | `test_skills`, `test_learnrepo_skill` | — | catalog empty | — | extend manifest with `integration` kind | P2 |
| GitHub | TESTED | health probes, `close_implemented`, CI gates | `test_authority_verifier` | EV-CI | cancelled runs on main (ISSUE-013) | — | main never cancelled | P1 |
| Drive | TESTED | `drive_bridge.py` (rclone, `MARK2_SHARED`) | `test_drive_bridge` | folder idle (EV-DRIVE) | Mark-2-specific remote | — | configurable remote; backup push | P2 |
| Mark-2 | PARTIAL | deployment contract, units, codex worker script | — | R-02 (secondhand) | DC-1 SHA unnamed; drift | TR-0-03 | verification/overflow host only | P2 |
| Backup / restore | CI_VERIFIED | `backup.py` (+encrypt), nightly maintenance, restore test | `test_backup_encryption`, CI job | — | off-host copy not automated | Drive config | nightly encrypted push + quarterly restore drill | P1 |
| Observability / heartbeat | TESTED | events, sessions, `today`, `usage`, `routing-report`, `supervisor`, `usage_telemetry` | `test_usage_telemetry`, `test_routing_report` | — | no cost-per-verified-task metric | — | add metric | P2 |
| Security / secrets / audit | CI_VERIFIED | `security.py` redact/scan, history scan, hash-chained audit export, 0600 env store, argv allowlist | `test_security`, `test_scan_history`, `test_audit_chain`, `test_secret_quoting` | — | flat secret namespace | — | scoped secret refs | P2 |
| CI / deploy / update / rollback | CI_VERIFIED / PARTIAL | CI 6 jobs + macOS; Mark-2 contract §7 rollback; no update script | — | EV-CI | no `aion update` (pull+verify+restart) command | — | `scripts/update.sh` with verify+rollback | P2 |
| Mac portability / clean bootstrap | TESTED (CI only) | host adapters, launchd, `platform_resolver`, portability ratchet | `test_launchd_units`, `test_host_adapter`, macOS job | never on a real Mac | launchd work agent not periodic; Login Items; Ollama/OpenClaw on Mac | phase 7 | `07_` | P2 |
| Project/company/app lifecycle | ABSENT | — | — | — | — | phase 5 | `06_` | P1 |
| First value workflow | PARTIAL | `sevaa.py` daily brief + reconcile, `money_path`, experiments | `test_sevaa` | `SEVAA_AUTOMATION_TOKEN` not set | owner token | phase 8 | nightly reconcile + WhatsApp `money` | P1 |

## Reading the matrix
- Engineering core (rows 1–6, 12, 17, 20, 21) is genuinely solid: tested, CI-verified on three Pythons and macOS, restore-tested, resume-tested.
- Every owner-facing edge (approvals from the phone, OpenClaw write path, LucyNest authority, executors) is PARTIAL or unproven live. That is the gap between "engineering healthy" and "operable".
- Multi-project/company is ABSENT by design so far; the seams to add it (project column, skills manifests, secret store, governor) exist and are cheap to extend.
