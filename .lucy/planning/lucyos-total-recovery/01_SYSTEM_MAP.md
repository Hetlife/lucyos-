# 01 — System map (verified edges)

Status vocabulary: ABSENT / DESIGNED / PARTIAL / IMPLEMENTED / TESTED / CI_VERIFIED / LIVE_VERIFIED / DEGRADED / BROKEN / DUPLICATED / OBSOLETE / UNKNOWN. "LIVE" claims need EV-LIVE-* and are secondhand until TR-0-04.

```
 owner (iPhone WhatsApp | LucyNest pad | AION Control PWA | terminal)
   |  A: transport             B: ingress/auth            C: authority
   v
 bridges/whatsapp_bridge.py (stdin|file|webhook|cloud)   bridges/http_server.py (token, SSE)   integrations/openclaw (skill + lucyosctl + SSH forced cmd)
   |  HMAC + verify token + sender allowlist + redaction        bearer token, loopback only            allowlisted verbs, read-mostly
   v
 aion_core/router.py  (regex commands; APPROVE/DENY strict)  ---> approvals.py (Tier-3 queue) ---> security.py (redact, scan)
   v
 AION control plane: db.py (SQLite truth) | tasks.py (state machine, evidence gate) | sessions.py | resume.py (boot/checkpoint) | governor.py + metrics.py (budget)
   v
 context.py / memory.py / recall (FTS; optional vec)  ->  skills.py / learnrepo.py (registry, lifecycle, review gate)
   v
 worker.py: DET argv allowlist | A Ollama | B aux free gateway or cloud cmd | C held | D approval   -> agents.py route
   v
 validation_command / output_location -> tasks.complete(evidence) -> events, model_usage, sessions -> reports.py / sync-docs (markdown views)
   v
 owner surfaces: status/today/money/tasks/blockers/why (WhatsApp) | api.py snapshot/events (PWA) | health.supervisor (LucyNest) | approvals card
```

## Edge table
| # | Edge | Implementation | Contract | Tests | Live state | Failure modes | State owner | Dup / gaps |
|---|---|---|---|---|---|---|---|---|
| E1 | WhatsApp (Meta Cloud) -> bridge | `whatsapp_bridge.py cloud` | GET handshake, POST HMAC-SHA256, 64 KiB cap, sender allowlist, 6 env vars | `test_bridge*`, `test_bridge_start_e2e`, `test_no_reverse_dns` | UNKNOWN; never reached a real phone (EV-PHONE) | crash-loop on missing vars (Restart=always 5 s); single-threaded; needs public HTTPS tunnel | secrets.env | Optional path; OpenClaw is primary |
| E2 | OpenClaw -> LucyOS | `integrations/openclaw/lucyos/*` | `lucyosctl {status,skills,health,learnrepo-status,tasks,approvals,context,route,architecture-check,work-dry}` local or SSH forced command | `test_openclaw_lucyos_bridge` (1 skip) | reachable on Lucy-den per R-05 (secondhand) | no write verbs: cannot approve/deny/pause via this path; default `AION_HOME=/root/...` | AION DB | **Gap G-A**: governed write/approve verb absent |
| E3 | PWA / phone -> http_server | `bridges/http_server.py` + `web/` | `/api/{status,...}`, `/api/command` (router), `/api/v1/{snapshot,events,stream,tasks,projects,money,costs}`, SCS task/result handoff | `test_http_interface`, `test_http_v1`, `test_sse_events` | UNKNOWN (service exists; tunnel needed) | token in page; loopback only | AION DB | second UI on PR #2 branch (`phone.py`) = OBSOLETE |
| E4 | LucyNest pad -> bridge | branch only: `devices/little_lucy/bridge.py` + native client | paired TLS + bearer, GET /status, POST /decision | branch tests | LIVE on Nebula 192.168.31.122 per checkpoint (secondhand); touch broken | approval authority undecided (read-only vs secondary) | AION DB via bridge | not on main; TS design-system package also on branch |
| E5 | Router -> approvals | `router.py`, `approvals.py` | only `APPROVE <ID>` / `DENY <ID>` decide; one task held per approval | `test_router`, `test_approvals`, `test_end_to_end` | CI_VERIFIED | none known | DB `approvals` | — |
| E6 | Tasks state machine | `tasks.py` TRANSITIONS, evidence gate, `close_implemented`, heartbeat/progress | READY->CLAIMED->RUNNING->DONE with evidence; RECOVERY table by failure kind | `test_tasks`, `test_task_reliability`, `test_recovery_injection` | CI_VERIFIED | — | DB `tasks` | `sqlite3` import in tasks.py flagged by boundary ratchet (type hint only) |
| E7 | Resume / crash recovery | `resume.py boot()`: verify brain, ingest inbox, release stale claims, name bottleneck | RESUME.md pointer; idempotent | `clean-bootstrap-health` job, `test_recovery_injection` | CI_VERIFIED | — | `<AION_HOME>/RESUME.md` + DB | — |
| E8 | Routing + governor | `agents.route(kind, complexity, stakes, ambiguity)`; `governor.enforce` demotes C->B->A; handoff at STOP | DET->A->B->C->D; budget INR 200/day, 2000/month | `test_routing_and_state`, `test_plan_worker`, `test_model_gateway` | CI_VERIFIED; no cloud/local executor configured in CI | one global cloud command; no per-project policy | DB `agents`, `model_usage`, `meta` | `feature/resource-governor` = DUPLICATED (rejected) |
| E9 | Execution | `worker.py` argv allowlist, `_do_work`, `_validate` | DET requires exec_command; A/B need validation_command or output_location else NEEDS_REVIEW; C held; D approval | `test_plan_worker`, R-01 hardening | R-02 DET proof on Mark-2 (secondhand) | executors absent -> WAITING with saved work order | DB | context compiler (#73) waiting; context_pack branch = superseded |
| E10 | Plans | `plan.py` validate/apply | JSON PLAN -> dependency-ordered tasks; refuses unverifiable steps | `test_plan_worker` | CI_VERIFIED | — | DB | — |
| E11 | Memory / context | `memory.py` (FTS5), `context.py build(task_id)`, `recall/` (lexical; optional vec) | derived indexes rebuildable | `test_semantic_recall` (skip w/o vec), `test_context_contract` | CI_VERIFIED | no project scoping | DB `memory` | 3 context generations (main / context-pack / #73) |
| E12 | Skills / LearnRepo | `skills.py` registry+manifest+catalog+lifecycle; `learnrepo.py` schedules/leases/health/review gate; `.claude/skills/learnrepo` | manifest schema; lifecycle gated by review | `test_skills`, `test_learnrepo*` | CI_VERIFIED; catalog empty | — | DB `skills`, `learnrepo_*` | nearest seam for the integration contract |
| E13 | Health / verify / supervisor | `health.py` (20 checks, deep), `aion verify`, `supervisor_snapshot` | measured, never assumed; authority drift non-blocking | `test_verify`, `test_supervisor`, `ci_health_gate.py` | CI_VERIFIED | — | — | — |
| E14 | Backup / restore / export | `backup.py` (restore-tested, optional encryption), `portability.py export/import` | secrets never included | `test_backup_encryption`, `test_portability_export`, CI job | CI_VERIFIED; off-host drill documented, not evidenced | Drive upload not automated | `<AION_HOME>/BACKUPS` | — |
| E15 | Services | `systemd/*` (bridge, interface, work timer 10 min, maintenance 03:15, mark2-drive) ; `deploy/launchd/*` | rendered by `install_services.sh`; `@REPO@ @AION_HOME@` | `test_launchd_units` | Lucy-den/Mark-2 UNKNOWN | `PATH=/root/.local/bin` in units; launchd work agent not periodic | host | — |
| E16 | Drive | `bridges/drive_bridge.py` via rclone, `gdrive:MARK2_SHARED` fixed | staged, scanned docs; never DB | `test_drive_bridge`, `test_drive_check` | Drive folder idle since 09-09 (EV-DRIVE) | Mark-2 specific naming | Drive | — |
| E17 | GitHub | `health.check_github_*`, `tasks.close_implemented` (Task-ID trailer), CI | verifier read from base branch | authority tests | CI_VERIFIED | main SHAs with cancelled CI (EV-CI-CANCEL) | GitHub | — |
| E18 | Authority | `verify_authority.py` strict/anti-dup/self/deploy; `HIGH_MODEL_BASELINE.json`; module manifests; boundary ratchet | protected + constitutional paths; task overrides | `test_authority_verifier`, `test_module_manifests`, `test_check_boundaries` | CI_VERIFIED; self-drift 5 | drift always red -> ignored | baseline | — |
| E19 | SEVAA (first business app) | `sevaa.py`: HMAC events, daily brief, payment reconcile, approvals proxy; `money_path.py`; `PROJECTS/sevaa-sales-os` | tokens from secret store | `test_sevaa`, `test_money_path` | token not configured (health) | — | DB `finance`, `deliveries` | model for the integration contract |
| E20 | TaskCheck | `taskcheck.py` + `taskcheck_server.py` + `taskcheck_web/` | tokenised public checklist windows tied to tasks | `test_taskcheck*` | UNKNOWN | — | DB `taskcheck_*` | Cloudflare variant on `feature/taskcheck-mvp` = separate product, archive |
| E21 | Mark-2 | deployment contract, `aion_codex_worker.sh`, `mark2-drive` units | exact-SHA deploy, verify, rollback | — | DC-1 never named (EV-LIVE-M2) | hard-coded `/root/lucyos`, codex path | — | — |
| E22 | SCG / device trust | branch only (`gateway.py`) | COSE_Sign1 device-signed `status.read` | branch tests | not merged | third-party deps; edits CI | — | DESIGNED/IMPLEMENTED-on-branch, rejected as-is |

## Sources of truth (declared and actual)
| Thing | Declared truth | Actual | Verdict |
|---|---|---|---|
| Operational state | `<AION_HOME>/state/aion.sqlite3` on the primary machine | same; markdown regenerated by `sync-docs` | keep |
| Code | `origin/main` | same; 58 UNIQUE branches carry unmerged work | keep; drain branches |
| Authority | `.lucy/authority/*` frozen at `2a70020` | drifted 5 files | re-freeze (TR-0-03) |
| Plans / task lists | (none declared) | 6 generations of plan files | this package (TR-0-02 marks the rest historical) |
| Owner interface | WhatsApp via OpenClaw | OpenClaw path is read-only; Meta bridge unproven | TR-1-03 + TR-3-01 |
| Secrets | `private_state/secrets.env` (0600) | same; single flat namespace | keep; scope later (TR-5-07) |
| Drive | transport only (C2) | idle since 2026-09-09; backup folder empty of automation | keep as transport; automate backup push (TR-2-02) |
