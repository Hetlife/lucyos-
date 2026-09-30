# 05 — Target architecture

## Decision in one paragraph
Keep AION as the kernel: one SQLite truth, deterministic router, evidence-gated tasks, approvals, governor, resume, health, backup. Do not rewrite, do not add a second control plane, do not adopt third-party orchestration. Add three thin layers on the existing seams: (1) a **governed command envelope** so every interface (OpenClaw/WhatsApp, PWA, LucyNest, CLI, SSH) submits the same authenticated message to the same router; (2) a **workspace/project layer** that turns the existing `project` column into real, policy-carrying entities; (3) an **integration contract** that reuses the skill manifest so apps (SEVAA, Drive, GitHub, future CRM/email) install per workspace/project with scoped secret references, without touching `aion_core`.

## Layers (target)
```
L0 Host        Linux systemd | macOS launchd      host adapter, AION_HOME, secrets.env(0600), Ollama, tunnels
L1 Kernel      db.py tasks approvals sessions resume governor metrics security backup health   (protected; unchanged shape)
L2 Identity+   command envelope: {channel, principal, key_id, nonce, text|action}  -> router  (HMAC stdlib; per-channel adapters)
   authority   workspace/project policy: allowed classes, caps, approval rules, data class ceiling
L3 Context     memory + recall + context compiler, scoped by project; knowledge roots per project; LearnRepo
L4 Capability  skills registry (kind: skill | integration); manifests declare scopes, secret_refs, actions, events, health
L5 Execution   executor registry: DET | ollama | claude-code | codex | aux-free | strong-session; per class, per project policy
L6 Verification validation_command / output_location / evidence; sessions; events; audit chain
L7 Surfaces    OpenClaw+WhatsApp (primary), AION Control PWA, LucyNest pad (read-only until D-4), CLI
```

## Keep (unchanged or minor)
- `aion_core/*` as listed in the baseline; all 795 tests; CI shape; module manifests; boundary ratchet; authority verifier.
- `integrations/openclaw/lucyos` as the OpenClaw contract (extend, don't replace).
- `web/` + `api.py` as the phone UI; `health.supervisor_*` as the LucyNest feed.
- `sevaa.py`, `money_path.py`, `experiments.py`, `deliveries.py`: they are the first real business workload.
- `portability.py export/import`, `backup.py`: the migration primitives.

## Repair
- OpenClaw write path (ISSUE-011). CI cancellation on main (ISSUE-013). Root defaults (ISSUE-016). Authority re-freeze (ISSUE-010). Boundary warnings (ISSUE-015). launchd periodic loop (ISSUE-024). Off-host backup (ISSUE-021). Update/rollback script (ISSUE-023). Executor registry (ISSUE-028).

## Add (new, on existing seams)
| Addition | Seam reused | New surface |
|---|---|---|
| Command envelope + `whatsapp` verb over OpenClaw | `router.handle`, `db.log_event`, `security.redact`, `lucyosctl` | `lucyosctl whatsapp "<text>"`; envelope logged with `principal`, `key_id` |
| `workspaces`, `projects`, `project_integrations` tables; `aion workspace|project|integration` commands | `db._migrate` additive; `project` column becomes FK-by-convention | `PROJECTS/<id>/project.json` definition; `<AION_HOME>/PROJECTS/<id>/` state |
| Project policy in routing | `agents.route`, `governor.enforce`, `worker._work_locked` | `max_class`, `monthly_cap_inr`, `approval_required_kinds`, `data_class_ceiling` |
| Integration manifests | `skills/manifest.schema.json`, `skills.register_manifest`, `learnrepo.review_gate` | `kind: integration`, `scopes`, `secret_refs`, `actions`, `reads`, `events`, `health_command`, `cost_class`, `rate_limit` |
| Scoped secrets | `config.secrets_file`, `aion secrets` | names `WS_<workspace>__NAME` and `PJ_<project>__NAME`; resolver picks the narrowest scope |
| Executor registry | `agents` table (`agent_id`, `model_class`, `enabled`), `worker.run_cloud` | `executors` rows with `command_template`, `class`, `host`, `timeout_s`; portable worker scripts in `scripts/executors/` |
| Update/rollback | Mark-2 contract §1–§7 | `scripts/update.sh <sha>` on any host |

## Stop / reject
- Second governor (`feature/resource-governor`), vendored third-party skill (`feature/unlazy-completion`), Cloudflare TaskCheck, third context generation (`feature/context-pack`), COSE gateway with third-party crypto (as-is), `aion_core/phone.py` (PR #2).
- New `aion_core` top-level modules unless the baseline records them first.
- Any design that makes Mark-2, Drive, WhatsApp, OpenClaw or LucyNest a second source of truth.
- Enterprise multi-tenant machinery (RBAC matrices, per-tenant databases). One owner, one SQLite, namespaced rows and scoped policy are enough for years.

## Codebase reduction (from S-41/S-42 evidence, still valid)
- `fable.py` (678 lines, launch-pack generator) and `seed.py` mission tasks are bootstrap-era. Freeze; do not extend. Candidate for removal once this package replaces the "Fable pack" as the handoff mechanism (owner decision D-8).
- `directives/` (8 prompt files) and `docs/MASTER_AI_*` duplicate `.lucy/handoffs`; keep one entry point (`START_HERE.md`) and archive the rest (TR-0-02).
- Three TaskCheck surfaces (Python subsystem, web assets, branch Cloudflare app): keep the Python one only.

## Invariants (machine-checked today, keep)
1. Stdlib-only core. 2. Every state write and outbound message passes `security.redact`. 3. `tasks.complete` refuses empty evidence. 4. Only `APPROVE/DENY <ID>` decide approvals. 5. One SQLite truth; markdown is generated. 6. Protected/constitutional paths change only through Fable-authored, owner-merged PRs. 7. No second queue/scheduler/approval engine/secret store (anti-dup). 8. Loopback binding plus tunnels; never `0.0.0.0`.
