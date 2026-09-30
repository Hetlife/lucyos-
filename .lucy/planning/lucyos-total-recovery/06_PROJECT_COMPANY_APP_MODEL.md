# 06 — Project / company / app model

## Decision
- **Company = workspace.** A workspace is a namespace with shared policy, secrets scope, knowledge roots and a set of projects. No separate "tenant" or "org" concept. Personal work lives in workspace `het`.
- **Project = first-class entity** (today it is a string). It owns objective, repos, knowledge roots, agents/skills, integrations, model/compute policy, budgets, approval rules, schedules, health, evidence, lifecycle.
- **App / integration = a skill manifest with `kind: integration`.** Installed once, enabled per workspace or project, holding secret *references* only.
- **Isolation = scoping, not separate databases.** Rows carry `workspace_id`/`project_id`; secrets are name-scoped; context/recall filter by project; policy is enforced in `agents.route`, `governor.enforce`, `worker`.

## Schema (additive migration, schema v13; `db.py` protected -> Fable override TR-5-02)
```sql
CREATE TABLE IF NOT EXISTS workspaces (
  workspace_id TEXT PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL DEFAULT 'company',   -- company | personal
  status TEXT NOT NULL DEFAULT 'ACTIVE', policy_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS projects (
  project_id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(workspace_id),
  name TEXT NOT NULL, objective TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'ACTIVE',  -- ACTIVE|PAUSED|ARCHIVED
  definition_path TEXT NOT NULL DEFAULT '', policy_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS project_integrations (
  project_id TEXT NOT NULL, skill_id TEXT NOT NULL, scope TEXT NOT NULL DEFAULT 'project',  -- project | workspace
  enabled INTEGER NOT NULL DEFAULT 1, config_json TEXT NOT NULL DEFAULT '{}', installed_at TEXT NOT NULL,
  PRIMARY KEY(project_id, skill_id));
-- existing `project` TEXT columns on tasks/finance/deliveries/memory/intake keep their name; values must match projects.project_id.
-- migration: INSERT workspace 'het' (personal) and one project per distinct existing value ('default' -> 'het-default', 'sevaa-sales-os' -> workspace 'sevaaconnect').
```
Policy JSON (both levels; project overrides workspace, never widens beyond it):
```json
{"max_model_class":"B","monthly_cap_inr":500,"daily_cap_inr":100,"approval_required_kinds":["real_money","production_deploy"],
 "data_class_ceiling":"CONFIDENTIAL","allowed_executors":["DET","ollama","claude-code"],"knowledge_roots":["PROJECTS/strategy-factory/knowledge"],
 "repos":["github.com/Hetlife/strategy-factory"],"schedules":[{"cron":"daily 07:00","command":"sevaa-reconcile"}]}
```

## Repo-side definition (versioned) vs runtime state
```
PROJECTS/<project_id>/project.json      definition: workspace, objective, policy, integrations, knowledge roots, repos   (git)
PROJECTS/<project_id>/money_path.json   optional, already used by sevaa-sales-os
<AION_HOME>/PROJECTS/<project_id>/      runtime: knowledge index, work orders, evidence, exports                        (state, backed up)
COMPANIES/<workspace_id>/workspace.json definition: name, kind, default policy, secret scope name                      (git)
```
`aion project sync` registers/updates DB rows from the definitions (idempotent), the same way `skills.sync_catalog` does for manifests.

## Integration contract (extends `skills/manifest.schema.json`)
| Field | Meaning |
|---|---|
| `kind: "integration"` | distinguishes from `skill` |
| `provider` | `github`, `google-drive`, `whatsapp`, `sevaa`, `email`, `crm`, `custom` |
| `scopes[]` | least-privilege capabilities: `read:tasks`, `write:finance`, `send:message`, `read:drive:MARK2_SHARED`, ... (checked by `worker`/`router` before an action runs) |
| `secret_refs[]` | names only, resolved from the scoped store at run time; never values |
| `reads[]`, `actions[]`, `events[]` | declared operations; each action has `risk_class` (`read`, `write`, `money`, `external_commitment`) and `approval` (`none`, `owner`) |
| `health_command` | deterministic probe; surfaces in `aion health` per project |
| `cost_class`, `rate_limit` | `free`, `metered`; requests/min |
| `install.enable`, `install.disable`, `install.revoke` | idempotent commands; revoke must invalidate secrets/tokens it created |
| `sandbox` | how to run against a test tenant; `version` semver |
Lifecycle reuses `skills.set_lifecycle` + `learnrepo.review_gate` (candidate -> reviewed -> enabled -> disabled -> revoked). Every action logs an event with `project_id`, `skill_id`, `scope`, `principal`.

## Minimum flows
CLI (WhatsApp/OpenClaw verbs mirror these; PWA shows the same objects):
```
aion workspace create sevaaconnect --kind company
aion project create strategy-factory --workspace sevaaconnect --objective "..." --repo github.com/Hetlife/strategy-factory
aion integration install skills/catalog/comm/whatsapp-openclaw.manifest.json
aion integration enable github --project strategy-factory --scopes read:repo,write:pr
aion secrets set PJ_strategy-factory__GITHUB_TOKEN
aion task-add "Draft Q4 offer page" --project strategy-factory --kind write --model-class B
aion work --max 5                       # routes under project policy; raises approval if kind is in approval_required_kinds
WhatsApp: "approve A-12" | "status strategy-factory" | "tasks sevaaconnect"
aion why TASK-XXXX | aion context TASK-XXXX   # evidence
```
Owner UX rule: creating a project must never require editing `aion_core`; it is files + two commands.

## Isolation matrix
| Concern | Mechanism | Enforced in |
|---|---|---|
| Permissions | policy JSON + integration scopes | `agents.route`, `worker.check_command`/action gate, `router` |
| Knowledge | `knowledge_roots` indexed under `memory.kind='knowledge:<project>'`; recall filters by project | `memory.py`, `context.py`, #73 compiler |
| Memory | `project` column on memory rows; cross-project reads require `--all` and log an event | `memory.search` |
| Models | `max_model_class`, `allowed_executors` | `governor.enforce`, `worker._work_locked` |
| Compute | executor host per project (`local`, `mark2`, `mac`) | executor registry |
| Secrets | scoped names; resolver never falls back upward from project to workspace to global unless the manifest says `inherit: true` | `config`/`secrets` resolver |
| Budgets | per-project caps under the global cap; governor demotes per project | `metrics.budget_status(project)` |
| Evidence | events and sessions tagged with project | `db.log_event` |
