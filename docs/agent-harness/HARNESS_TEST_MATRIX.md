# Verification matrix — truthful execution states
- W1 schema malformed/extra property/type/status/timestamps: automated negative tests, tests/test_agent_harness.py.
- Worker self-PASS/empty evidence: automated negative tests; no actual task mutation.
- Out-of-scope paths/path traversal: automated negative tests.
- Secrets in output / unsourced PASS tests: automated negative tests.
- Retry without evidence and untrusted injection summary: automated negative tests.
- W2 context stale SHA, byte cap, file cap, source hash, no full repository: automated tests.
- W3 live model routing budgets/fallback: NOT_TESTED (no changes to protected router/governor).
- W4 lease concurrency/expiration, restart-replay, verifier progression: NOT_TESTED in this milestone.
- W5 real independent executor loop and WhatsApp E2E delivery: NOT_TESTED until evidence recorded.
Run: python3 -m unittest tests.test_agent_harness; python3 -m unittest discover -s tests -q; ./aion scan .; authority strict/anti-dup; portability/boundaries.

- W2b multi-agent review: registered skill validation, history-based ranking, mutation overlap denial, protected-scope denial, reviewer independence, task/baseline binding, dissent-over-majority fail-closed, and uncertainty escalation: tests/test_agent_collaboration.py.
- W2b host-level isolated AION pilot: real canonical task TASK-43B58F01 completed after 3 real schema tests (exit 0), blocked sibling TASK-7454BC12 preserved, fresh process confirmed statuses, team proposal and dispute CLI exercised. TEMP STATE ONLY; production promotion and external model E2E NOT_TESTED.

- W2 source tamper detection: tests/test_agent_packet_freshness.py (SHA, digest and on-disk file hash; rejects stale uncommitted sources).
- Existing AION event replay: tests/test_agent_review_durability.py checks one durable review ACK, same-ID duplicate, changed-content collision, forged sender, and unrelated task rejection.
