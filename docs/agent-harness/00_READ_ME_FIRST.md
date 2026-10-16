# LucyOS Agent Harness — W1/W2 bootstrap
Scope: candidate branch task/TR-AGENT-HARNESS-20261016; baseline GitHub main e349bb03446452bace3a5225d990a73bae8160e1 as of 2026-10-16. NOT deployed.
Read existing root START_HERE.md and .lucy/authority/PROTECTED_PATHS.md first. AION SQLite remains operational truth; do not duplicate queue/approvals/governor.
- Envelope shape and validation: schemas/agent-message.schema.json, aion_core/packets.py:validate_agent_envelope.
- SHA-pinned bounded context: aion_core/context.py:compile_agent_packet and ./aion context TASK-ID --harness-role cheap --slice tests/base.py:1:6.
- Existing AION CLI envelope check: ./aion envelope-validate <json-file> [--allowed-path tests/]. This only confirms shape/bounds; does not authorize or run any mutation.
- Schemas: schemas/work-order.schema.json, schemas/result.schema.json (views only).
- Tests: tests/test_agent_harness.py; run python3 -m unittest tests.test_agent_harness.
- Read SYSTEM_MAP_AND_REALITY.md, EVIDENCE_INDEX.md, OWNER_HANDOFF_AND_WHATSAPP_REPORT.md for honest status.

Collaboration: read AI_COLLABORATION_AND_DISPUTE.md. Advisory CLI: ./aion agent-rank CAPABILITY; ./aion agent-team-plan TASK-PARENT assignments.json; ./aion agent-dispute result.json reviews.json. All three are non-dispatching proposals.

Durable review helper (for trusted AION internal caller only): packets.record_authenticated_agent_review; MUST supply a separately verified transport principal. No direct public API is enabled.
