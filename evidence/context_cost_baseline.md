# S-43 context cost baseline

Measurement tree: `66e3a4ef1b8242123555af5a7c9d80115ab23d82` (canonical main).
Reference commits supply touched paths; all content and import edges are measured
on this single canonical tree, not on six different historical snapshots.
This is an offline deterministic context proxy, not actual files opened or model
usage telemetry. Approx tokens = total file bytes / 4; no prompt/completion token
or cost claim is made.

## Reproduction

Run from the S-43 task checkout, with the canonical commit in the local object store:

```bash
measurement_tree=$(mktemp -d /tmp/s43-context.XXXXXX)
git archive 66e3a4ef1b8242123555af5a7c9d80115ab23d82 | tar -x -C "$measurement_tree"
for ref in 3131c9d 2b59aea 612f5ef 1f28fd4 08406e3 6510ec9; do
  mapfile -t touched < <(git diff-tree --root --no-commit-id --name-only -r "$ref")
  python3 scripts/task_context_profiler.py --root "$measurement_tree" --files "${touched[@]}"
done
```

The CLI takes a file list (the card's alternative to a commit argument), emits
sorted JSON, and performs no subprocess or network calls. Both executions of
each reference, including reversed touched-file order, produced identical results.
Python AST imports are resolved to repository modules, including relative imports
and package initializers. One forward/backward hop is anchored only to the
original touched set; then tests importing any expanded file are added without
further expansion. Dynamic imports are not inferred. Missing touched files or
invalid Python fail explicitly instead of silently lowering counts.

The governance route is START_HERE itself, its explicit existing Markdown, text,
and JSON file routes, plus routes in its designated docs/README index. It is a
conservative union of conditional routes, not an assertion that every task needs
all these documents. Cross-references in the resulting documents are not followed.
External/live-state paths and directories are not read. All selected non-Python
files count as docs/instructions, including touched metadata. LOC counts physical
lines including blanks/comments and an unterminated final line. Files are deduped;
tokens use original bytes, including UTF-8 multibyte characters.

## Six reference tasks

| Task type | Task | Reference commit | Files | Source LOC | Docs LOC | Approx tokens (bytes/4) |
|---|---|---|---:|---:|---:|---:|
| Small bug fix | S-08 | `3131c9dafca0882b909d7355cf5d7f218fa9ed10` | 84 | 12618 | 1239 | 158796.75 |
| New skill | Q006 | `2b59aea7d785bbc42139dcb361834bb48ae158a3` | 113 | 16216 | 1265 | 197708.00 |
| Provider/adapter | S-10 | `612f5effea25bb0db3c40a7930a5b1c2d3b9595e` | 62 | 5267 | 1239 | 78140.75 |
| Persistence | S-13 | `1f28fd4738157e4703480af2c8874673dfa9dc77` | 104 | 15036 | 1239 | 184638.75 |
| Cross-node | S-23 | `08406e30bba1f7a6da8d0cfeb5e2d6e49b812869` | 98 | 14351 | 1239 | 178757.00 |
| Project-specific | S-29 | `6510ec964ce9fbbbd07db353a2663c7a7bd0e1f4` | 98 | 14351 | 1239 | 178757.00 |

## Governance LOC an agent following START_HERE reads

**1239 LOC** across **9 files**, computed once
on the canonical tree and included (deduplicated) in every row. This measured
routing rule replaces the scorecard's unverified ≥1,500-line statement.

- `.lucy/authority/HIGH_MODEL_BASELINE.json`: 220 LOC
- `.lucy/execution/SONNET_TASK_QUEUE.md`: 469 LOC
- `START_HERE.md`: 32 LOC
- `docs/ARCHITECTURE.md`: 65 LOC
- `docs/OPERATIONS.md`: 181 LOC
- `docs/README.md`: 10 LOC
- `docs/WHATSAPP_COMMANDS.md`: 59 LOC
- `docs/skill-system/Q000_ARCHITECTURE_AUDIT.txt`: 169 LOC
- `docs/skill-system/Q006_ARCHITECTURE_ANTI_DUPLICATION.txt`: 34 LOC

## Exact context sets

### S-08

Touched: `aion_core/security.py`, `tests/test_security.py`.

- `.lucy/authority/HIGH_MODEL_BASELINE.json`
- `.lucy/execution/SONNET_TASK_QUEUE.md`
- `START_HERE.md`
- `aion_core/__init__.py`
- `aion_core/approvals.py`
- `aion_core/cli.py`
- `aion_core/context.py`
- `aion_core/db.py`
- `aion_core/errors.py`
- `aion_core/fable.py`
- `aion_core/handoff.py`
- `aion_core/intake.py`
- `aion_core/learnrepo.py`
- `aion_core/memory.py`
- `aion_core/model_gateway.py`
- `aion_core/notebook.py`
- `aion_core/packets.py`
- `aion_core/plan.py`
- `aion_core/reports.py`
- `aion_core/router.py`
- `aion_core/security.py`
- `aion_core/sessions.py`
- `aion_core/skills.py`
- `aion_core/sync_outbox.py`
- `aion_core/tasks.py`
- `aion_core/usage_telemetry.py`
- `aion_core/worker.py`
- `bridges/drive_bridge.py`
- `bridges/http_server.py`
- `bridges/whatsapp_bridge.py`
- `docs/ARCHITECTURE.md`
- `docs/OPERATIONS.md`
- `docs/README.md`
- `docs/WHATSAPP_COMMANDS.md`
- `docs/skill-system/Q000_ARCHITECTURE_AUDIT.txt`
- `docs/skill-system/Q006_ARCHITECTURE_ANTI_DUPLICATION.txt`
- `scripts/scan_history.py`
- `tests/base.py`
- `tests/test_api.py`
- `tests/test_approvals.py`
- `tests/test_architecture.py`
- `tests/test_audit_chain.py`
- `tests/test_autonomy_days.py`
- `tests/test_backup_encryption.py`
- `tests/test_bridge.py`
- `tests/test_context_contract.py`
- `tests/test_delivery_economics.py`
- `tests/test_drive_bridge.py`
- `tests/test_drive_check.py`
- `tests/test_end_to_end.py`
- `tests/test_experiments.py`
- `tests/test_guardian.py`
- `tests/test_host_adapter.py`
- `tests/test_http_interface.py`
- `tests/test_http_v1.py`
- `tests/test_intake.py`
- `tests/test_learnrepo.py`
- `tests/test_migrations.py`
- `tests/test_model_gateway.py`
- `tests/test_money_path.py`
- `tests/test_monthly_close.py`
- `tests/test_notebook_sessions.py`
- `tests/test_openclaw_check.py`
- `tests/test_openclaw_independence.py`
- `tests/test_packets.py`
- `tests/test_plan_worker.py`
- `tests/test_platform_resolver.py`
- `tests/test_portability_export.py`
- `tests/test_recovery_injection.py`
- `tests/test_router.py`
- `tests/test_routing_and_state.py`
- `tests/test_routing_report.py`
- `tests/test_runtime_inventory.py`
- `tests/test_security.py`
- `tests/test_seed.py`
- `tests/test_semantic_recall.py`
- `tests/test_skills.py`
- `tests/test_sse_events.py`
- `tests/test_sync_outbox.py`
- `tests/test_task_data_class.py`
- `tests/test_tasks.py`
- `tests/test_tempworker.py`
- `tests/test_usage_telemetry.py`
- `tests/test_util.py`

### Q006

Touched: `aion_core/__init__.py`, `aion_core/architecture.py`, `aion_core/cli.py`, `docs/skill-system/Q006_ARCHITECTURE_ANTI_DUPLICATION.txt`, `skills/architecture-proposal.example.json`, `tests/test_architecture.py`.

- `.lucy/authority/HIGH_MODEL_BASELINE.json`
- `.lucy/execution/SONNET_TASK_QUEUE.md`
- `START_HERE.md`
- `aion_core/__init__.py`
- `aion_core/agents.py`
- `aion_core/api.py`
- `aion_core/approvals.py`
- `aion_core/architecture.py`
- `aion_core/autonomy.py`
- `aion_core/backup.py`
- `aion_core/bootstrap.py`
- `aion_core/cli.py`
- `aion_core/config.py`
- `aion_core/context.py`
- `aion_core/db.py`
- `aion_core/deliveries.py`
- `aion_core/errors.py`
- `aion_core/experiments.py`
- `aion_core/fable.py`
- `aion_core/governor.py`
- `aion_core/guardian.py`
- `aion_core/handoff.py`
- `aion_core/health.py`
- `aion_core/intake.py`
- `aion_core/learnrepo.py`
- `aion_core/memory.py`
- `aion_core/metrics.py`
- `aion_core/milestones.py`
- `aion_core/model_gateway.py`
- `aion_core/money_path.py`
- `aion_core/notebook.py`
- `aion_core/owner_setup.py`
- `aion_core/packets.py`
- `aion_core/plan.py`
- `aion_core/platform_resolver.py`
- `aion_core/portability.py`
- `aion_core/recall/lexical.py`
- `aion_core/reports.py`
- `aion_core/resume.py`
- `aion_core/router.py`
- `aion_core/security.py`
- `aion_core/seed.py`
- `aion_core/semantic_recall.py`
- `aion_core/sessions.py`
- `aion_core/skills.py`
- `aion_core/sync_outbox.py`
- `aion_core/tasks.py`
- `aion_core/tempworker.py`
- `aion_core/usage_telemetry.py`
- `aion_core/util.py`
- `aion_core/worker.py`
- `bridges/__init__.py`
- `bridges/drive_bridge.py`
- `bridges/http_server.py`
- `bridges/openclaw_check.py`
- `bridges/whatsapp_bridge.py`
- `docs/ARCHITECTURE.md`
- `docs/OPERATIONS.md`
- `docs/README.md`
- `docs/WHATSAPP_COMMANDS.md`
- `docs/skill-system/Q000_ARCHITECTURE_AUDIT.txt`
- `docs/skill-system/Q006_ARCHITECTURE_ANTI_DUPLICATION.txt`
- `scripts/ci_health_gate.py`
- `scripts/runtime_inventory.py`
- `scripts/scan_history.py`
- `skills/architecture-proposal.example.json`
- `tests/base.py`
- `tests/test_api.py`
- `tests/test_approvals.py`
- `tests/test_architecture.py`
- `tests/test_audit_chain.py`
- `tests/test_autonomy_days.py`
- `tests/test_backup_encryption.py`
- `tests/test_bridge.py`
- `tests/test_context_contract.py`
- `tests/test_delivery_economics.py`
- `tests/test_drive_bridge.py`
- `tests/test_drive_check.py`
- `tests/test_end_to_end.py`
- `tests/test_experiments.py`
- `tests/test_guardian.py`
- `tests/test_host_adapter.py`
- `tests/test_http_interface.py`
- `tests/test_http_v1.py`
- `tests/test_intake.py`
- `tests/test_learnrepo.py`
- `tests/test_migrations.py`
- `tests/test_model_gateway.py`
- `tests/test_money_path.py`
- `tests/test_monthly_close.py`
- `tests/test_notebook_sessions.py`
- `tests/test_openclaw_check.py`
- `tests/test_openclaw_independence.py`
- `tests/test_packets.py`
- `tests/test_plan_worker.py`
- `tests/test_platform_resolver.py`
- `tests/test_portability_export.py`
- `tests/test_recovery_injection.py`
- `tests/test_router.py`
- `tests/test_routing_and_state.py`
- `tests/test_routing_report.py`
- `tests/test_runtime_inventory.py`
- `tests/test_security.py`
- `tests/test_seed.py`
- `tests/test_semantic_recall.py`
- `tests/test_skills.py`
- `tests/test_sse_events.py`
- `tests/test_sync_outbox.py`
- `tests/test_task_data_class.py`
- `tests/test_tasks.py`
- `tests/test_tempworker.py`
- `tests/test_usage_telemetry.py`
- `tests/test_util.py`

### S-10

Touched: `aion_core/host/__init__.py`, `aion_core/host/base.py`, `aion_core/host/linux.py`, `aion_core/host/macos.py`, `tests/test_host_adapter.py`.

- `.lucy/authority/HIGH_MODEL_BASELINE.json`
- `.lucy/execution/SONNET_TASK_QUEUE.md`
- `START_HERE.md`
- `aion_core/__init__.py`
- `aion_core/host/__init__.py`
- `aion_core/host/base.py`
- `aion_core/host/linux.py`
- `aion_core/host/macos.py`
- `aion_core/platform_resolver.py`
- `docs/ARCHITECTURE.md`
- `docs/OPERATIONS.md`
- `docs/README.md`
- `docs/WHATSAPP_COMMANDS.md`
- `docs/skill-system/Q000_ARCHITECTURE_AUDIT.txt`
- `docs/skill-system/Q006_ARCHITECTURE_ANTI_DUPLICATION.txt`
- `scripts/runtime_inventory.py`
- `tests/base.py`
- `tests/test_api.py`
- `tests/test_approvals.py`
- `tests/test_architecture.py`
- `tests/test_audit_chain.py`
- `tests/test_autonomy_days.py`
- `tests/test_backup_encryption.py`
- `tests/test_bridge.py`
- `tests/test_context_contract.py`
- `tests/test_delivery_economics.py`
- `tests/test_drive_bridge.py`
- `tests/test_end_to_end.py`
- `tests/test_experiments.py`
- `tests/test_guardian.py`
- `tests/test_host_adapter.py`
- `tests/test_http_interface.py`
- `tests/test_http_v1.py`
- `tests/test_intake.py`
- `tests/test_learnrepo.py`
- `tests/test_migrations.py`
- `tests/test_model_gateway.py`
- `tests/test_money_path.py`
- `tests/test_monthly_close.py`
- `tests/test_notebook_sessions.py`
- `tests/test_openclaw_check.py`
- `tests/test_openclaw_independence.py`
- `tests/test_packets.py`
- `tests/test_plan_worker.py`
- `tests/test_platform_resolver.py`
- `tests/test_portability_export.py`
- `tests/test_recovery_injection.py`
- `tests/test_router.py`
- `tests/test_routing_and_state.py`
- `tests/test_routing_report.py`
- `tests/test_runtime_inventory.py`
- `tests/test_security.py`
- `tests/test_seed.py`
- `tests/test_semantic_recall.py`
- `tests/test_skills.py`
- `tests/test_sse_events.py`
- `tests/test_sync_outbox.py`
- `tests/test_task_data_class.py`
- `tests/test_tasks.py`
- `tests/test_tempworker.py`
- `tests/test_usage_telemetry.py`
- `tests/test_util.py`

### S-13

Touched: `aion_core/db.py`, `aion_core/sync_outbox.py`, `tests/test_sync_outbox.py`.

- `.lucy/authority/HIGH_MODEL_BASELINE.json`
- `.lucy/execution/SONNET_TASK_QUEUE.md`
- `START_HERE.md`
- `aion_core/__init__.py`
- `aion_core/agents.py`
- `aion_core/api.py`
- `aion_core/approvals.py`
- `aion_core/autonomy.py`
- `aion_core/backup.py`
- `aion_core/bootstrap.py`
- `aion_core/cli.py`
- `aion_core/config.py`
- `aion_core/context.py`
- `aion_core/db.py`
- `aion_core/deliveries.py`
- `aion_core/errors.py`
- `aion_core/experiments.py`
- `aion_core/fable.py`
- `aion_core/governor.py`
- `aion_core/handoff.py`
- `aion_core/health.py`
- `aion_core/intake.py`
- `aion_core/learnrepo.py`
- `aion_core/memory.py`
- `aion_core/metrics.py`
- `aion_core/milestones.py`
- `aion_core/model_gateway.py`
- `aion_core/money_path.py`
- `aion_core/notebook.py`
- `aion_core/packets.py`
- `aion_core/plan.py`
- `aion_core/portability.py`
- `aion_core/recall/lexical.py`
- `aion_core/reports.py`
- `aion_core/resume.py`
- `aion_core/router.py`
- `aion_core/security.py`
- `aion_core/seed.py`
- `aion_core/semantic_recall.py`
- `aion_core/sessions.py`
- `aion_core/skills.py`
- `aion_core/sync_outbox.py`
- `aion_core/tasks.py`
- `aion_core/tempworker.py`
- `aion_core/usage_telemetry.py`
- `aion_core/util.py`
- `aion_core/worker.py`
- `bridges/http_server.py`
- `bridges/openclaw_check.py`
- `bridges/whatsapp_bridge.py`
- `docs/ARCHITECTURE.md`
- `docs/OPERATIONS.md`
- `docs/README.md`
- `docs/WHATSAPP_COMMANDS.md`
- `docs/skill-system/Q000_ARCHITECTURE_AUDIT.txt`
- `docs/skill-system/Q006_ARCHITECTURE_ANTI_DUPLICATION.txt`
- `scripts/ci_health_gate.py`
- `tests/base.py`
- `tests/test_api.py`
- `tests/test_approvals.py`
- `tests/test_architecture.py`
- `tests/test_audit_chain.py`
- `tests/test_autonomy_days.py`
- `tests/test_backup_encryption.py`
- `tests/test_bridge.py`
- `tests/test_context_contract.py`
- `tests/test_delivery_economics.py`
- `tests/test_drive_bridge.py`
- `tests/test_drive_check.py`
- `tests/test_end_to_end.py`
- `tests/test_experiments.py`
- `tests/test_guardian.py`
- `tests/test_host_adapter.py`
- `tests/test_http_interface.py`
- `tests/test_http_v1.py`
- `tests/test_intake.py`
- `tests/test_learnrepo.py`
- `tests/test_migrations.py`
- `tests/test_model_gateway.py`
- `tests/test_money_path.py`
- `tests/test_monthly_close.py`
- `tests/test_notebook_sessions.py`
- `tests/test_openclaw_check.py`
- `tests/test_openclaw_independence.py`
- `tests/test_packets.py`
- `tests/test_plan_worker.py`
- `tests/test_platform_resolver.py`
- `tests/test_portability_export.py`
- `tests/test_recovery_injection.py`
- `tests/test_router.py`
- `tests/test_routing_and_state.py`
- `tests/test_routing_report.py`
- `tests/test_runtime_inventory.py`
- `tests/test_security.py`
- `tests/test_seed.py`
- `tests/test_semantic_recall.py`
- `tests/test_skills.py`
- `tests/test_sse_events.py`
- `tests/test_sync_outbox.py`
- `tests/test_task_data_class.py`
- `tests/test_tasks.py`
- `tests/test_tempworker.py`
- `tests/test_usage_telemetry.py`
- `tests/test_util.py`

### S-23

Touched: `aion_core/cli.py`, `aion_core/portability.py`, `tests/test_portability_export.py`.

- `.lucy/authority/HIGH_MODEL_BASELINE.json`
- `.lucy/execution/SONNET_TASK_QUEUE.md`
- `START_HERE.md`
- `aion_core/__init__.py`
- `aion_core/agents.py`
- `aion_core/approvals.py`
- `aion_core/architecture.py`
- `aion_core/autonomy.py`
- `aion_core/backup.py`
- `aion_core/bootstrap.py`
- `aion_core/cli.py`
- `aion_core/config.py`
- `aion_core/context.py`
- `aion_core/db.py`
- `aion_core/deliveries.py`
- `aion_core/errors.py`
- `aion_core/experiments.py`
- `aion_core/fable.py`
- `aion_core/governor.py`
- `aion_core/handoff.py`
- `aion_core/health.py`
- `aion_core/learnrepo.py`
- `aion_core/memory.py`
- `aion_core/metrics.py`
- `aion_core/milestones.py`
- `aion_core/money_path.py`
- `aion_core/notebook.py`
- `aion_core/owner_setup.py`
- `aion_core/packets.py`
- `aion_core/plan.py`
- `aion_core/platform_resolver.py`
- `aion_core/portability.py`
- `aion_core/reports.py`
- `aion_core/resume.py`
- `aion_core/router.py`
- `aion_core/security.py`
- `aion_core/seed.py`
- `aion_core/sessions.py`
- `aion_core/skills.py`
- `aion_core/tasks.py`
- `aion_core/util.py`
- `aion_core/worker.py`
- `bridges/__init__.py`
- `bridges/drive_bridge.py`
- `bridges/openclaw_check.py`
- `docs/ARCHITECTURE.md`
- `docs/OPERATIONS.md`
- `docs/README.md`
- `docs/WHATSAPP_COMMANDS.md`
- `docs/skill-system/Q000_ARCHITECTURE_AUDIT.txt`
- `docs/skill-system/Q006_ARCHITECTURE_ANTI_DUPLICATION.txt`
- `tests/base.py`
- `tests/test_api.py`
- `tests/test_approvals.py`
- `tests/test_architecture.py`
- `tests/test_audit_chain.py`
- `tests/test_autonomy_days.py`
- `tests/test_backup_encryption.py`
- `tests/test_bridge.py`
- `tests/test_context_contract.py`
- `tests/test_delivery_economics.py`
- `tests/test_drive_bridge.py`
- `tests/test_drive_check.py`
- `tests/test_end_to_end.py`
- `tests/test_experiments.py`
- `tests/test_guardian.py`
- `tests/test_host_adapter.py`
- `tests/test_http_interface.py`
- `tests/test_http_v1.py`
- `tests/test_intake.py`
- `tests/test_learnrepo.py`
- `tests/test_migrations.py`
- `tests/test_model_gateway.py`
- `tests/test_money_path.py`
- `tests/test_monthly_close.py`
- `tests/test_notebook_sessions.py`
- `tests/test_openclaw_check.py`
- `tests/test_openclaw_independence.py`
- `tests/test_packets.py`
- `tests/test_plan_worker.py`
- `tests/test_platform_resolver.py`
- `tests/test_portability_export.py`
- `tests/test_recovery_injection.py`
- `tests/test_router.py`
- `tests/test_routing_and_state.py`
- `tests/test_routing_report.py`
- `tests/test_runtime_inventory.py`
- `tests/test_security.py`
- `tests/test_seed.py`
- `tests/test_semantic_recall.py`
- `tests/test_skills.py`
- `tests/test_sse_events.py`
- `tests/test_sync_outbox.py`
- `tests/test_task_data_class.py`
- `tests/test_tasks.py`
- `tests/test_tempworker.py`
- `tests/test_usage_telemetry.py`
- `tests/test_util.py`

### S-29

Touched: `aion_core/cli.py`, `aion_core/experiments.py`, `aion_core/money_path.py`, `tests/test_experiments.py`, `tests/test_money_path.py`.

- `.lucy/authority/HIGH_MODEL_BASELINE.json`
- `.lucy/execution/SONNET_TASK_QUEUE.md`
- `START_HERE.md`
- `aion_core/__init__.py`
- `aion_core/agents.py`
- `aion_core/approvals.py`
- `aion_core/architecture.py`
- `aion_core/autonomy.py`
- `aion_core/backup.py`
- `aion_core/bootstrap.py`
- `aion_core/cli.py`
- `aion_core/config.py`
- `aion_core/context.py`
- `aion_core/db.py`
- `aion_core/deliveries.py`
- `aion_core/errors.py`
- `aion_core/experiments.py`
- `aion_core/fable.py`
- `aion_core/governor.py`
- `aion_core/handoff.py`
- `aion_core/health.py`
- `aion_core/learnrepo.py`
- `aion_core/memory.py`
- `aion_core/metrics.py`
- `aion_core/milestones.py`
- `aion_core/money_path.py`
- `aion_core/notebook.py`
- `aion_core/owner_setup.py`
- `aion_core/packets.py`
- `aion_core/plan.py`
- `aion_core/platform_resolver.py`
- `aion_core/portability.py`
- `aion_core/reports.py`
- `aion_core/resume.py`
- `aion_core/router.py`
- `aion_core/security.py`
- `aion_core/seed.py`
- `aion_core/sessions.py`
- `aion_core/skills.py`
- `aion_core/tasks.py`
- `aion_core/util.py`
- `aion_core/worker.py`
- `bridges/__init__.py`
- `bridges/drive_bridge.py`
- `bridges/openclaw_check.py`
- `docs/ARCHITECTURE.md`
- `docs/OPERATIONS.md`
- `docs/README.md`
- `docs/WHATSAPP_COMMANDS.md`
- `docs/skill-system/Q000_ARCHITECTURE_AUDIT.txt`
- `docs/skill-system/Q006_ARCHITECTURE_ANTI_DUPLICATION.txt`
- `tests/base.py`
- `tests/test_api.py`
- `tests/test_approvals.py`
- `tests/test_architecture.py`
- `tests/test_audit_chain.py`
- `tests/test_autonomy_days.py`
- `tests/test_backup_encryption.py`
- `tests/test_bridge.py`
- `tests/test_context_contract.py`
- `tests/test_delivery_economics.py`
- `tests/test_drive_bridge.py`
- `tests/test_drive_check.py`
- `tests/test_end_to_end.py`
- `tests/test_experiments.py`
- `tests/test_guardian.py`
- `tests/test_host_adapter.py`
- `tests/test_http_interface.py`
- `tests/test_http_v1.py`
- `tests/test_intake.py`
- `tests/test_learnrepo.py`
- `tests/test_migrations.py`
- `tests/test_model_gateway.py`
- `tests/test_money_path.py`
- `tests/test_monthly_close.py`
- `tests/test_notebook_sessions.py`
- `tests/test_openclaw_check.py`
- `tests/test_openclaw_independence.py`
- `tests/test_packets.py`
- `tests/test_plan_worker.py`
- `tests/test_platform_resolver.py`
- `tests/test_portability_export.py`
- `tests/test_recovery_injection.py`
- `tests/test_router.py`
- `tests/test_routing_and_state.py`
- `tests/test_routing_report.py`
- `tests/test_runtime_inventory.py`
- `tests/test_security.py`
- `tests/test_seed.py`
- `tests/test_semantic_recall.py`
- `tests/test_skills.py`
- `tests/test_sse_events.py`
- `tests/test_sync_outbox.py`
- `tests/test_task_data_class.py`
- `tests/test_tasks.py`
- `tests/test_tempworker.py`
- `tests/test_usage_telemetry.py`
- `tests/test_util.py`

## Validation

- `python3 -m unittest tests.test_task_context_profiler -v`: 5 passed.
- `python3 -m compileall -q aion_core bridges tests scripts`: passed.
- `python3 -m unittest discover -s tests -t . -q`: 567 tests in 57.284 s,
  OK (1 skip); suite increased by the five S-43 tests.
- `./aion scan .`: clean, no credential-shaped content.
- `python3 scripts/check_portability.py`: 0 violations, 3 known exceptions,
  0 stale exceptions.
- `python3 .claude/skills/smallest-fix/scripts/check_reinvention.py scripts/task_context_profiler.py tests/test_task_context_profiler.py`:
  no likely reinvention.
- Six baseline measurements repeated identically; the standalone CLI's S-08 JSON
  was byte-identical to the recorded measurement JSON.
- Pre-change `anti-dup` and `strict` authority gates against `origin/main`: both
  `ok: true`. Post-commit commands:
  `python3 scripts/verify_authority.py anti-dup --base origin/main` and
  `python3 scripts/verify_authority.py strict --base origin/main --branch task/S-43-context-profiler`.
