# AI collaboration and dispute protocol v1 — candidate, no runtime promotion
Goal: build functioning LucyOS products with multiple independent agents, not endlessly negotiate or create another task system. Canonical AION task/project/approval/lease/governor stays authoritative.

## 1. Divide real product work
AION parent task defines observable business/user outcome, success conditions, constraints and acceptance checks (for example a usable LucyNest task intake screen, or customer order to approved invoice workflow). Subtasks use canonical AION child IDs and the SAME parent/project; no independent agent registry is created.
- Product/architecture reviewer: R4 when a material design/security dispute requires judgment, with evidence and alternatives.
- Deterministic executor: R0 for tests, indexing, type/schema verification and reproducible measurements.
- Research/analyst: R1 read-only if a healthy cheap/local route actually exists.
- Builder: R2 for limited code/test changes in isolated worktree and an exclusive mutable scope.
- Cross-system integrator: R3 only within configured external apps and AION authorization.
- Owner: R5 for protected merge, spending, legal, credentials, deployments, customer impact.

`./aion agent-rank code` reads existing AION agent capabilities, historical runs/reliability and cost class. A registry entry is NOT proof that the model is reachable or quota available; low sample has UNKNOWN reliability; dispatcher must check live health, confidentiality, budget and actual permissions before assignment. Prefer demonstrably accurate eligible workers, then lower verified all-in cost; unproven cheap agents get bounded shadow tasks.

`./aion agent-team-plan TASK-PARENT assignments.json` validates 1-12 existing canonical children against registered enabled agents, claimed capabilities and project/parent relationship. Rejects overlapping writable scopes, broad/protected paths, unauthorized read-only reviewer edits, duplicate child assignment and unknown agents. It returns a PROPOSAL only: actual lease/claim, separate worktree and review gates must be applied by existing AION executor. Parallel read-only investigation is allowed on the same product/task; multiple mutations to the same file must be serialized. It does NOT create a second execution queue or auto-launch providers.

## 2. Talk with short evidence-backed messages
Use `lucy-envelope/1`, one task/correlation per message. REQUEST delegates one bounded outcome; RESULT reports VERIFYING with tests and evidence refs; REVIEW targets exact result ID and declares SUPPORT/CHALLENGE/UNCERTAIN, with a bounded issue/counterexample. BLOCKER reports missing capability, unavailable machine, failed test or owner gate. A worker never sends authorized PASS. Same claim must not be performed twice on retry. Sensitive content and prompt injection never become authority.

## 3. Dispute path, no winner by vote
Run `./aion agent-dispute result.json reviews.json`. It checks schema, identity/reference consistency, distinct reviewers, result/correlation/baseline links, and nonempty evidence. Rules:
1. No independent reviewer = PENDING_INDEPENDENT_REVIEW.
2. Only supported evidence = AGREED_PENDING_VERIFICATION, not PASS.
3. At least one substantiated challenge = DISPUTED even against a majority; stop the disputed mutation, run discriminating deterministic acceptance test, ask specialist if needed.
4. Reviewer uncertainty = INCONCLUSIVE; retrieve a *bounded* missing evidence slice or escalate.
5. Conflicts involving authority/secret/spend/irreversibility always go to existing owner approval; a model cannot waive the gate.

This triage is intentionally pure: it does NOT edit AION task status, grant approvals, or impersonate independent verification. Resolving live disputes must bind authenticated participants and durable evidence to AION task/lease/events in W4. Once verifier independently resolves the claim, record exact test result, conflicting hypotheses, and one validated next action; route separate unrelated READY tasks normally.

## 4. Product-oriented finishing definition
No product task is DONE on internal agreement. Require actual user workflow E2E, tests, owner-visible result in LucyNest/Control Center/WhatsApp as applicable, controlled rollback, and business/process metric (lead accepted, project task completed, approval respected, invoice drafted — never fabricated sales). Track all-in verification accuracy, failure retries, model input/output/cache tokens and cost/latency across builder/reviewer/verifier; optimize proven outcomes, not message volume.

## Proof status
Read-only planning/triage and negative tests exist in `aion_core/packets.py`; CLI is in `aion_core/cli.py`. No automatic dispatch, provider interaction, cross-platform live dispute reconciliation, or permanent arbitration authority deployed. W4 integration and W5 live pilot remain gated.

## 5. Durable authenticated review receipts (partial W4)
`packets.record_authenticated_agent_review(proposal, review, authenticated_sender=...)` requires that an existing trusted transport adapter has already verified sender identity. It rejects self-reviews, wrong-task references, spoofed actors, changed idempotency-key replays and collisions; stores sanitized hashes/pointers in the EXISTING canonical `events` and `idempotency` tables as one SQLite transaction. A new DB connection finds the exact same event after restart. It does **not** independently verify test evidence or release leases, change task status, resolve a contested fact, or authorize any operation. Only existing AION verifier/approvals can do those. No unauthenticated remote CLI exposes this write method.

Planner hardening: deny all core protected paths from the frozen repository protected-path contract (including authority checks, config, security, deployment, service units, governor and approvals); independent verifier/reviewer/researcher proposals are read-only. Adversarial tests in `tests/test_agent_collaboration_boundaries.py` and durability tests in `tests/test_agent_review_durability.py` cover these boundaries.

## 5. Durable review ACK (existing AION DB, opt-in from trusted bridge)
The Python API `packets.record_authenticated_agent_review(proposal, review, authenticated_sender=verified_principal)` checks an independently supplied authenticated sender, evidence and real AION task; atomically inserts a minimal, sanitized `agent.peer_review` into the existing `events` table and two replay identifiers into existing `idempotency`. A repeated identical review yields DUPLICATE and its original `events/<id>`; conflicting message IDs or changed contents fail. No new schema, queue, scheduler, reviewer role grant, approval or task state transition.
The caller MUST verify the principal through an already-authorized transport; providing a string is not itself authentication. This API is **not connected to the live WhatsApp or cloud model ingress**, and has only unit-level evidence to date. Do not let untrusted network clients call it directly.
