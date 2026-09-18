# Complexity hotspots

Scope: Python files under aion_core, bridges, integrations and scripts; tests excluded. Package __init__.py files count as modules.

LOC counts physical lines. Function length spans def through its final statement (including nested definitions, excluding decorators). Imports include conditional and function-local imports; fan-in/out count distinct internal modules, not external libraries or dynamic imports. Named submodules resolve before package attributes. Self-imports are retained.

Production modules: 68. DFS back-edge cycles: 11.

Cycles use sorted DFS roots and neighbors and list each back edge once; this is not enumeration of all elementary cycles. Counts can differ from the ad hoc 67-module / 14-cycle baseline as scripts are added or traversal and import-resolution conventions differ.

## Top 12 by LOC

- `aion_core.fable`: 678
- `aion_core.learnrepo`: 669
- `aion_core.worker`: 615
- `bridges.drive_bridge`: 602
- `aion_core.cli`: 601
- `aion_core.db`: 569
- `aion_core.skills`: 455
- `scripts.check_portability`: 352
- `aion_core.reports`: 349
- `bridges.whatsapp_bridge`: 318
- `scripts.verify_authority`: 270
- `aion_core.packets`: 255

## Top 12 by Fan-in

- `aion_core.db`: 43
- `aion_core.util`: 39
- `aion_core.security`: 26
- `aion_core.config`: 25
- `aion_core.tasks`: 17
- `aion_core.memory`: 13
- `aion_core.errors`: 11
- `aion_core.metrics`: 11
- `aion_core.approvals`: 10
- `aion_core.resume`: 10
- `aion_core.agents`: 9
- `aion_core.skills`: 8

## Top 12 by Fan-out

- `aion_core.cli`: 39
- `aion_core.worker`: 15
- `aion_core.reports`: 14
- `aion_core.fable`: 13
- `aion_core.resume`: 12
- `aion_core.api`: 11
- `aion_core.health`: 11
- `aion_core.handoff`: 10
- `aion_core.router`: 10
- `aion_core.learnrepo`: 8
- `aion_core.packets`: 8
- `bridges.whatsapp_bridge`: 8

## Top 12 by function length

- `aion_core.cli._main`: 564
- `aion_core.fable._start_prompt`: 111
- `aion_core.experiments.status`: 90
- `aion_core.fable._offline_prompt`: 89
- `bridges.drive_bridge.Bridge.pull`: 88
- `aion_core.worker._work_locked`: 82
- `aion_core.portability.import_`: 74
- `aion_core.handoff.build_prompt`: 71
- `aion_core.worker._execute`: 66
- `aion_core.resume.boot`: 64
- `aion_core.skills.validate_manifest`: 64
- `aion_core.learnrepo.execute_run`: 63

## Cycles

- `aion_core.approvals` → `aion_core.tasks` → `aion_core.resume` → `aion_core.approvals`
- `aion_core.tasks` → `aion_core.resume` → `aion_core.bootstrap` → `aion_core.notebook` → `aion_core.tasks`
- `aion_core.approvals` → `aion_core.tasks` → `aion_core.resume` → `aion_core.bootstrap` → `aion_core.skills` → `aion_core.learnrepo` → `aion_core.governor` → `aion_core.handoff` → `aion_core.approvals`
- `aion_core.resume` → `aion_core.bootstrap` → `aion_core.skills` → `aion_core.learnrepo` → `aion_core.governor` → `aion_core.handoff` → `aion_core.resume`
- `aion_core.tasks` → `aion_core.resume` → `aion_core.bootstrap` → `aion_core.skills` → `aion_core.learnrepo` → `aion_core.governor` → `aion_core.handoff` → `aion_core.tasks`
- `aion_core.tasks` → `aion_core.resume` → `aion_core.bootstrap` → `aion_core.skills` → `aion_core.learnrepo` → `aion_core.governor` → `aion_core.tasks`
- `aion_core.skills` → `aion_core.learnrepo` → `aion_core.skills`
- `aion_core.tasks` → `aion_core.resume` → `aion_core.bootstrap` → `aion_core.skills` → `aion_core.learnrepo` → `aion_core.tasks`
- `aion_core.approvals` → `aion_core.tasks` → `aion_core.resume` → `aion_core.packets` → `aion_core.approvals`
- `aion_core.tasks` → `aion_core.resume` → `aion_core.packets` → `aion_core.tasks`
- `aion_core.tasks` → `aion_core.resume` → `aion_core.tasks`
