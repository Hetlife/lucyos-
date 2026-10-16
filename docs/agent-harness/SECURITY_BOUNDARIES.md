# Boundary and verifier requirements
Authority source: .lucy/authority/** frozen constitutional paths; see PROTECTED_PATHS.md and platform/data contracts. Do not edit database schema, approval logic, worker, router, governor, service units or deployed OpenClaw from this W1/W2 branch.
Envelope schema validates shape; validate_agent_envelope additionally denies worker self-PASS, invalid status/type, unjustified retry, unscoped file edits, unsourced test PASS, credential-like content. It does NOT authenticate sender or allow mutation; canonical AION lease and approval must be checked in a future integration gate.
Context compiler is read-only and pinned to git SHA + content hashes. Injection in source content cannot grant authority; any future worker must treat it as untrusted.
Approval-required messages never constitute approvals. Evidence refs are pointers, not independently validated proof; use AION's existing deterministic verifier and task completion controls.
Known gaps: true verifier binding, lease expiry E2E, replay/idempotent transport ACK, live owner WhatsApp receipt, failure isolation under the autonomous scheduler — tracked in work orders.
