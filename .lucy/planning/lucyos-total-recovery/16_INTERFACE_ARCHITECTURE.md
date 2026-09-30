# 16 — Interface architecture: Control Center, LucyNest, OpenClaw + WhatsApp

## Decision
No new frontend. The **Main LucyOS Control Center is `web/` + `bridges/http_server.py` + `aion_core/api.py`** (the existing "AION Control" PWA, 629 lines, token-authenticated, loopback + tunnel, SSE live events). It grows by adding read models to `api.py` and sections to one page, in the order below. Every input it takes goes through `router.handle` or an existing CLI seam; it owns no state.

Rejected: a Node/React stack (PR #53 itself concluded "KEEP / BUILD NATIVE"; the Drive design reference says extend `bridges/http_server.py` + `web/`), Framer (no repo artefacts; design-only), a Cloudflare app, the LucyNest TypeScript design-system package (separate repo candidate for the pad's visual language, not the Control Center).

## Control Center: what exists vs the required list
| Required | Exists today | Add |
|---|---|---|
| Overview / health / bottleneck / next action | `/api/v1/snapshot`, health dot, budget bar | — |
| Companies / projects | `/api/v1/projects` (derived from distinct strings) | reads `projects`/`workspaces` tables after TR-5-02; project switcher = query param `?project=` |
| Task queue + running work | `/api/v1/tasks`, `/api/v1/live-activity` | RUNNING/WAITING/BLOCKED grouping; task detail = `aion why` output (TR-I-01) |
| Approvals | `/api/approvals` + confirm-before-decide | — |
| Agents / workers / executors | `aion agents`, `capabilities` (CLI only) | `/api/v1/agents` (TR-I-01) |
| Machines | none | `/api/v1/machines`: this host's `health.machine()` + `meta.host_role`; other hosts appear when they push a census (TR-I-02) |
| Model / executor routing | `routing-report` (CLI) | `/api/v1/routing` (TR-I-02) |
| Integrations / apps | none | `/api/v1/integrations` after TR-5-04 |
| Evidence / results | events, `why` | per-task evidence panel (TR-I-01) |
| Errors / blockers | `/api/blockers`, `/api/errors` | — |
| Logs | sessions (`aion session`) | `/api/v1/sessions` (TR-I-02) |
| Schedules / automations | timers only | `/api/v1/schedules` from host adapter + project policy (phase 5) |
| Memory / knowledge | `aion search` | `/api/v1/search?q=` (TR-I-02) |
| Cost / tokens | `/api/v1/costs` | + per-verified-task after TR-2-05 |
| Work input (global and scoped) | `/api/command` (router grammar), offline capture queue | `task-add` verb with `--project` via router grammar `add <project>: <title>` (TR-I-01) |
Sequence: TR-I-01 (task detail, agents, command scoping) -> TR-I-02 (machines, routing, sessions, search) -> phase 5 views. All server-rendered JSON + vanilla JS; no build step; loopback only; tunnel for phone (Tailscale Serve).

## LucyNest role (decision, pending D-4 for approvals)
LucyNest = **glanceable status + one-tap owner input**, in two forms: the Nebula pad (native client, 480×272) and the "Lucy Nest" card in the PWA fed by `aion supervisor`. It reads `GET /status` projections and may POST an input that becomes a canonical task or approval decision through the same bridge/router path. It never holds state, never schedules, never decides on its own. Until D-4, decisions are display-only (`remote-decisions.enabled` stays off). Source lands as inactive code (TR-3-03).

## OpenClaw + WhatsApp role
OpenClaw = channel and bounded executor **below** LucyOS governance. WhatsApp text -> OpenClaw -> `lucyosctl whatsapp "<text>"` with `LUCYOS_PRINCIPAL` -> `router.handle` -> canonical state -> reply text. It handles: quick commands (`status`, `today`, `money`, `tasks`, `blockers`, `errors`, `agents`, `report`, `why`), owner actions (`approve/deny`, `pause/resume`, `safe mode`), notifications (morning routine, approval cards, governor alerts via `owner_alert` meta), lightweight evidence (`why <ID>`). It does not: store state, run unapproved shell, call paid models on its own, or bypass the router. Direct Meta bridge stays optional.

## Contract that binds all three (harness N)
1. Every interface input is a router message or an existing CLI/API verb; no interface has its own queue, approval table, or decision logic.
2. Every input carries `channel` and `principal`; events record both.
3. Reads are projections (`api.py`, `supervisor`, `reports`) and are redacted by `security.redact`.
4. Interfaces bind to loopback and reach the phone through a private tunnel; the only public endpoint is the optional Meta webhook.
