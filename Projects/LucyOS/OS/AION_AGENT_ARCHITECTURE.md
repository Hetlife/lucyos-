AION AGENT ARCHITECTURE
=======================

AION uses a deterministic-first specialist system to minimize model/API usage.

CORE
----
AION Core
- Orchestrator / Coordinator
- State Manager
- Task Router
- Recovery / Resume
- Cost Guard

SPECIALISTS
-----------
AION Intelligence
- Researcher
- Adversarial Reviewer
- Evidence Evaluator

AION Ops
- Deployment
- Monitoring
- Backup / Recovery
- Security / Secret Scan
- QA / Test Gate

AION Capital
- Unit Economics
- Cost Control
- Capital Allocation
- Experiment Budgeting
- Paper Money / Scenario Engine

AION Growth
- Prospect Data
- Content / Marketing
- Funnel / Experiment Tracking
- Conversion Analysis
- Compliance Gate

AION Ventures
- SEVAA Sales OS
- future business modules
- future validated opportunity experiments

TOKEN / COMPUTE RULES
---------------------
1. Deterministic scripts first.
2. Fingerprint inputs.
3. Skip unchanged workers.
4. Give each worker a narrow context pack.
5. No full-repo reread for routine cycles.
6. High-reasoning model only for ambiguous/high-value decisions.
7. QA/security acts as a gate, not a duplicate full agent.
8. Never put private_state into model context.
9. Do not create duplicate schedulers.
10. Persist exact resume state.

PRIMARY COMMANDS
----------------
Quick cycle:
    python scripts/agent_cycle.py --mode quick

Deep cycle:
    python scripts/agent_cycle.py --mode full

END
