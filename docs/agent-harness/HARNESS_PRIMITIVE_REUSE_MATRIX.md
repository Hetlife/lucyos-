# Primitive reuse audit
| Concern | Reused canonical implementation | New in this branch | Remaining gate |
|---|---|---|---|
| Work identity, DAG, claims | aion_core/tasks.py, db.py | Typed work-order schema view | Prove lease expiry and DAG isolation |
| Session, restart | sessions.py, resume.py | Checkpoint instructions | Restart/rehydration E2E |
| Agent messaging | packets.py AI SYNC legacy ingestion | Side-effect-free Lucy Envelope JSON Schema and validator in packets.py | Add authorized transport binding/durable ACK |
| Scoped context | context.py, recall/context_compiler.py | SHA-locked range capsule in context.py | Verify chosen real worker receives only capsule |
| Routing/spend | agents.py, router.py, governor.py, model_usage | Budget policy docs only | W3 permissioned integration, measurements |
| Verification | existing AION worker/task evidence handling | Refuse worker self-attested PASS at envelope boundary | W4 independent validator-to-task transition |
| Owner WhatsApp | existing Lucy-den OpenClaw WhatsApp default | Report template/hand-off file only | Approved send and provider ack |
| Host platforms | existing host/linux.py, host/macos.py | Portability notes | Mac E2E after availability |
Nothing above is a new DB, daemon, orchestration vendor or approval authority.

Review audit: aion_core/packets.py:record_authenticated_agent_review atomically reuses existing AION events and idempotency tables, with no new DB schema. Caller authenticates the principal via the existing approved channel; worker proposals cannot be verified or approved by this event.
