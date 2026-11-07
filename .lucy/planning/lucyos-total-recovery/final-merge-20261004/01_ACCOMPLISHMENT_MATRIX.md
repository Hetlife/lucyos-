# Accomplishments and limits
Evidence at baseline SHA; historical claims are not live proof.

| Capability | Status | Works/evidence | Missing proof or next action |
|---|---|---|---|
| Bootstrap/config | CI_VERIFIED | main CI and full suite | fresh-user bootstrap, portable service paths |
| DB/migrations | LIVE_VERIFIED for integrity only | both SQLite quick_checks OK, schema 12 | canonical ownership; cross-host restore/migration |
| AION/tasks/sessions/checkpoints | IMPLEMENTED / TESTED | live rows, timers; suite | complete task cycle and restart-resume |
| Leases/concurrency | TESTED | existing claims and host-local mechanisms | two-host ownership/fencing; loss recovery |
| Approvals/router | IMPLEMENTED; partial live evidence | strict verb changes merged; openclaw attribution in A-108/109 | fresh pending-negative probe; action-parameter binding |
| Authority/governor | DEGRADED | F1 overrides merged, six hash drifts | reviewed re-freeze; no security-gate bypass |
| Planner/executor | PARTIAL | cloud-command configured on both | named adapters, real verified execution |
| DET execution | PARTIAL | code tested | compiler coupling remains TR-1-06 |
| Model/free/local routing | PARTIAL | existing gateways; binaries present | measured cost/fallback; local-model policy conflict |
| Skills/registry/LearnRepo/Fable | IMPLEMENTED / TESTED | existing registry, tests | per-subsystem live invocation and contract checks |
| Memory/context | CI_VERIFIED on main; DEGRADED runtime | #73/#95 merged | deploy safely and verify foreign-log regression live |
| OpenClaw/WhatsApp | DEPLOYED / partial proof | gateways active; stored approval principals | phone->canonical task->verified result |
| LucyNest | BROKEN native control at observation | SSH works; bridge active | restore client/socket/bootstrap; phone UI/touch independently |
| SCG/device trust | DESIGNED / deferred | archived design material | no new parallel gateway required |
| Remote actions/RDC | LIVE_VERIFIED for read-only audit access | both machines and pad inspected | governed reboot remains separate security decision |
| Health/observability | DEGRADED | status visible | build_loop masks failure; camera crash loop |
| GitHub | LIVE_VERIFIED | repo, PR, main CI | delta checks on future candidate SHA |
| Drive | LIVE_VERIFIED for connector reads | existing folders/coordination read | machine backup upload/restore not proven |
| Backup/restore | TESTED / operational gap | local archive inventory; provider backup IDs | encrypted off-host archive and clean restore |
| Deployment/update/rollback | PARTIAL | units exist | clean runtime pin and bad-update rollback drill |
| TaskCheck | IMPLEMENTED / tested in suite | existing main code | real mobile evidence->canonical task receipt |
| Architecture gates | DEGRADED | boundary/portability pass | six authority drifts; acceptance tied to exact candidate |
| Projects/company/apps | PARTIAL / schema absent | project text field/definitions | workspaces/projects/integrations isolation & lifecycle |
| Control Center | PARTIAL | existing web/API | scoped create/inspect/approve + all required views |
| Mac | TESTED portability only | Linux check, existing adapters | real hardware install/restore/reboot |
| Value workflow | UNKNOWN repeatability | code/definitions exist | repeated useful outcomes with measured success/cost |
