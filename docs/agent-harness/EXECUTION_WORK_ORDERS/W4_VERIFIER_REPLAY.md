# W4 — verifier/lease/replay binding
Depends W1. Use existing task claim, DB events, approvals, worker evidence and resume instead of new infrastructure.
R2 implements authoritative ID/lease binding for envelopes, deterministic verification of exact acceptance tests, failure isolation and replay/idempotent ACK. Include negative tests: forged sender, worker PASS, wrong lease, stale hash, concurrent mutators, expired/recovered claim, sibling BLOCKED, no evidence, injected policy, protected action requiring owner.
Acceptance: only canonical verifier can mark PASS; new process reloads exact checkpoint; no duplicate work. Protect db.py, worker.py, approvals.py and resume.py without override. Owner/Fable review for any protected contract change.
