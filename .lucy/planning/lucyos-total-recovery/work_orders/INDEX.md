# Work orders index

| ID | Title | Executor | Depends | Fable review | Status |
|---|---|---|---|---|---|
| [TR-0-01](TR-0-01.md) | Owner PR decisions and merges | OWNER | none | YES | PARTLY |
| [TR-0-02](TR-0-02.md) | Planning hygiene: one CURRENT plan, dangling refs fixed | DETERMINISTIC | none | NO | DONE |
| [TR-0-03](TR-0-03.md) | Authority re-freeze | FABLE | TR-0-01 (#73 merged) | YES |  |
| [TR-0-04](TR-0-04.md) | Runtime census on Lucy-den, Mark-2 and the LucyNest pad | CODEX | none | NO |  |
| [TR-0-05](TR-0-05.md) | PR #73 (context compiler) verification and override | FABLE | none | YES | DONE |
| [TR-0-06](TR-0-06.md) | Archive tags and branch-delete script | CODEX | none | NO |  |
| [TR-1-01](TR-1-01.md) | CI: never cancel in-progress runs on main | FABLE | none | YES |  |
| [TR-1-02](TR-1-02.md) | Boundary ratchet to zero warnings | CLAUDE_CODE | none | NO |  |
| [TR-1-03](TR-1-03.md) | Governed `whatsapp` verb on the OpenClaw bridge | CLAUDE_CODE | none | YES |  |
| [TR-1-04](TR-1-04.md) | Bridge service restart policy | CLAUDE_CODE | owner decision D-5; Fable adds `"TR-1-04": ["systemd/aion-br | NO |  |
| [TR-1-05](TR-1-05.md) | Live E2E: OpenClaw -> status and approve on Lucy-den | OPENCLAW + OWNER | TR-1-03 merged and pulled on Lucy-den | NO |  |
| [TR-1-06](TR-1-06.md) | Decouple DET execution from the context compiler | CLAUDE_CODE | override `"TR-1-06": ["aion_core/worker.py"]` | YES |  |
| [TR-2-01](TR-2-01.md) | Clean-machine proof script | CLAUDE_CODE | none | NO |  |
| [TR-2-02](TR-2-02.md) | Configurable Drive remote and nightly encrypted backup push | CLAUDE_CODE | none | NO |  |
| [TR-2-03](TR-2-03.md) | Restore drill on Mark-2 from a Lucy-den archive | CODEX | TR-2-02 live | NO |  |
| [TR-2-04](TR-2-04.md) | Remove root and machine-specific defaults | CLAUDE_CODE | override `"TR-2-04": ["scripts/check_portability.py", "syste | NO |  |
| [TR-2-05](TR-2-05.md) | Cost per verified task metric | LOCAL_MODEL | none | NO |  |
| [TR-3-01](TR-3-01.md) | WhatsApp via OpenClaw live from the phone | OWNER + OPENCLAW | TR-1-03 merged; TR-1-05 done | NO |  |
| [TR-3-02](TR-3-02.md) | LucyNest authority decision | OWNER + FABLE | none | YES |  |
| [TR-3-03](TR-3-03.md) | Merge LucyNest source as inactive, tested code | CLAUDE_CODE | TR-3-02 (may merge before it as inactive source) | YES |  |
| [TR-3-04](TR-3-04.md) | Archive SCG/RPAB design docs; re-verify churn fix | CLAUDE_CODE | none | NO |  |
| [TR-4-01](TR-4-01.md) | Install Ollama on the primary host | OWNER | none | NO |  |
| [TR-4-02](TR-4-02.md) | Executor registry and portable worker scripts | CLAUDE_CODE | overrides recorded; TR-0-04 census (which binaries exist) | YES |  |
| [TR-4-03](TR-4-03.md) | Context compiler live on one B task | CODEX | TR-0-05, TR-4-02 | NO |  |
| [TR-4-04](TR-4-04.md) | Routing report with cost per verified task per executor | DETERMINISTIC | TR-2-05, TR-4-02 | NO |  |
| [TR-4-05](TR-4-05.md) | Independent verification step for model outputs | CLAUDE_CODE | TR-4-02 (executor registry) preferred but not required | NO |  |
| [TR-4-06](TR-4-06.md) | Alternative-path memo for blocked tasks | CLAUDE_CODE | none | NO |  |
| [TR-5-01](TR-5-01.md) | Ratify the project/company/app schema and record overrides | FABLE + OWNER | TR-0-03 | YES |  |
| [TR-5-02](TR-5-02.md) | Migration v13: workspaces, projects, project_integrations + CLI | CLAUDE_CODE | TR-5-01 | YES |  |
| [TR-5-03](TR-5-03.md) | Project scoping across tasks, memory, context, finance | CLAUDE_CODE | TR-5-02 | NO |  |
| [TR-5-04](TR-5-04.md) | Integration manifest kind and lifecycle commands | CLAUDE_CODE | TR-5-02 | YES |  |
| [TR-5-05](TR-5-05.md) | SEVAA as the first integration manifest | CLAUDE_CODE | TR-5-04 | NO |  |
| [TR-5-06](TR-5-06.md) | Project policy enforced in routing, governor and worker | CLAUDE_CODE | TR-5-02, TR-5-01 | YES |  |
| [TR-5-07](TR-5-07.md) | Scoped secrets resolver | CLAUDE_CODE | TR-5-02 | YES |  |
| [TR-6-01](TR-6-01.md) | Mark-2 DC-1 deploy at the named SHA | CODEX | TR-0-03 wrote the SHA | YES |  |
| [TR-6-02](TR-6-02.md) | Clean-machine proof on a fresh Mark-2 user | CODEX | TR-2-01 | NO |  |
| [TR-6-03](TR-6-03.md) | Cherry-pick verify_installed_services.py | CLAUDE_CODE | none | NO |  |
| [TR-6-04](TR-6-04.md) | update.sh with verify and rollback | CLAUDE_CODE | TR-6-03 | YES |  |
| [TR-7-01](TR-7-01.md) | launchd aion-work periodic loop | CLAUDE_CODE | override | NO |  |
| [TR-7-02](TR-7-02.md) | Execute the Mac runbook on the mini | OWNER + CODEX | phases 2, 4, 6; TR-7-01 | YES |  |
| [TR-7-03](TR-7-03.md) | Promote the Mac, demote Lucy-den, reboot test | CODEX + OWNER | TR-7-02 | YES |  |
| [TR-8-01](TR-8-01.md) | Set the SEVAA automation token | OWNER | none | NO |  |
| [TR-8-02](TR-8-02.md) | Nightly SEVAA reconcile and daily brief in maintenance | CLAUDE_CODE | TR-8-01 (live), TR-5-05 (manifest; optional) | NO |  |
| [TR-8-03](TR-8-03.md) | OpenClaw morning routine | OPENCLAW | TR-3-01 | NO |  |
| [TR-8-04](TR-8-04.md) | Second workload: strategy-factory project via the phase-5 path | OWNER + CLAUDE_CODE | TR-5-02..07, TR-4-02 | YES |  |
| [TR-C-01](TR-C-01.md) | Archive batch: stale work artefacts and decided proposals | DETERMINISTIC | override for deploy/queues | NO |  |
| [TR-C-02](TR-C-02.md) | Archive the four unreachable contract-skeleton modules | CLAUDE_CODE | none | NO |  |
| [TR-C-03](TR-C-03.md) | Consolidate skill-system design texts | CLAUDE_CODE | none | NO |  |
| [TR-C-04](TR-C-04.md) | Retire the Fable launch pack (after D-8) | CLAUDE_CODE | owner decision D-8 | YES |  |
| [TR-I-01](TR-I-01.md) | Control Center: task detail, agents view, project-scoped command | CLAUDE_CODE | none (project scoping waits for TR-5-03) | NO |  |
| [TR-I-02](TR-I-02.md) | Control Center: machines, routing, sessions, search | CLAUDE_CODE | TR-I-01 | NO |  |
| [TR-1-07](TR-1-07.md) | Guard: bridge messages that are not LucyOS commands must not become tasks | CLAUDE_CODE | TR-1-05 evidence | YES |  |

52 work orders. Phases: 0 reality, 1 control plane, 2 runtime, 3 interfaces, 4 executors, 5 projects, 6 deployment, 7 Mac, 8 value, C cleanup, I interface.
