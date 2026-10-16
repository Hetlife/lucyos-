# Execution order — one canonical AION authority
W0 VERIFIED: attach audit, Git main, local machine reachability, canonical state snapshots, dirty tree preservation.
W1/W2 candidate: schemas, validator and scoped context. Gate = unit/negative tests, security and full repo suite, independent artifact hash checks.
W3 pending (depends W1/W2): reconcile capability registry, budget circuit breakers and retry evidence, within protected policy gates; specialist/owner review before protected changes.
W4 pending (depends W1): bind envelope to AION task identity, lease and independent verifier; replay recovery, idempotent ACK, DAG sibling isolation tests.
W5 pending (depends W2-W4): real read-only R0 pilot, R1 only if configured, R2 bounded code fix, intentional failed validation, restart resume, WhatsApp actual send acknowledgement.
W6 pending (depends W5 and comparable measured baseline): compare >=10 paired runs, candidate shadow evaluation, no safety regression, gated canary.
Independent work: MAC portability docs and LucyNest/Control Center follow-ups, no production promotion or primary-host switch.

W2b collaboration proposal and dispute triage implemented/tested, dependent on W1 schema. Next W4 must make identity/claims/leases/verified evidence durable; current CLI validation DOES NOT change runtime state. W5 requires real external model collaboration only when provider health and budget are authorized.

W4 owner-reviewed integration task: connect transport-verified identities to record_authenticated_agent_review and canonical verifier/lease/approvals. Never expose raw callable unauthenticated over HTTP or WhatsApp. Prove idempotent end-to-end receipt then proceed to W5.
