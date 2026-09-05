# FABLE HANDOFF — session of 2026-09-05

TASK_ID: TASK-1BB538FF (revenue experiment), TASK-94945B7C (bridge security review); seeded here as TASK-E41AAF54 / TASK-DC0802E8 because the shared brain in this sandbox was ephemeral and re-seeded
STATUS: DONE for both class-C jobs; the queue behind them is PLANNED (three plans, zero C steps) and waits on the owner's three real-world steps

ACTIONS_TAKEN:
- Artifact 1 EXPERIMENT.md (EXP-001, paid ₹2,499 design consultation to 30 warm contacts, verdict by code) with experiment.json, contacts.csv, README, PAYMENT_LINK.template.md
- Artifact 3: incoming/plan-exp001-paid-consult.json (13 steps), plan-bridge-hardening.json (6), plan-t100-go-public.json (9); all pass `aion plan check`; plan 1 applied and executed in a fresh brain
- Artifact 2 docs/MILESTONE_LADDER.md: the wall is M3 (delegated delivery), not M6; capital entry points and amounts
- Artifact 4 docs/SECURITY_REVIEW.md: 2 critical + 2 high + 1 low fixed with tests, 2 medium accepted and queued, rest accepted with reasons
- New control-layer capability, generic per project: aion_core/experiments.py (`aion experiment(s)`), aion_core/money_path.py (`aion path`), phone dashboard cards "Steps to real money" and the experiment funnel, `status` lines "EXP-001: …" and "Needs you: …"
- Worker fix: owner (class D) steps now complete after approval via their validation_command; denied cards cancel
- Bridge fixes: owner-number allowlist, JSON content-type required, fail-closed off loopback, socket timeout, content-length validation, bytes compare; router free text is class-D triage
- Logs and loop: docs/FINDINGS_LOG.md (finding → correction → left for cheap model; "needs strong" table), deploy/routines/DAILY_CHEAP_LOOP.md and WEEKLY_STRONG_REVIEW.md, OWNER_README.md

FILES_CHANGED: see `git show --stat HEAD` on branch claude/fable-deploy-setup-mc5nr6
TESTS_RUN: python3 -m unittest discover -s tests -t . -q → see FABLE_SESSION_LOG.md for the final count; `aion scan .` clean
MEASURED_RESULTS: M0 not reached (0 evidenced rows) — correct; EXP-001 NOT_STARTED, 0/30 sent; money path 1/8 done
FAILURES: none open; the seeded DET tasks without exec_command (Ollama install, backup, financial position) fail in the loop and escalate to WAITING — pre-existing, logged, not this session's scope
RISKS: the working branch and `main` diverged (main has a parallel earlier phone interface); routines push to the working branch only; a cheap session must not merge main
ASSUMPTIONS: price ₹2,499 is a hypothesis (no prior consult price known); Razorpay fee 2.36% ESTIMATE; warm-contact count UNKNOWN until the owner counts
APPROVALS_OPENED: in a fresh brain plan 1 raises three cards (payment link + unknowns; send 30 messages; deliver and record). On Mark-2 they appear after `aion plan apply`.
SPEND_INR: this session ran inside the owner's Claude Code plan, not against API credit; the harness exposes no INR figure. See FABLE_SESSION_LOG.md for the token-based ESTIMATE. `aion usage` was not recorded in the ephemeral brain because it would have been lost; the durable record is the session log.
NEXT_RECOMMENDED_ACTION: owner does money-path step 3 (payment link + five answers, 15 min); the daily cheap loop executes plan 1's B steps; then step 4 (send 30 messages)
EXACT_RESUME_POINT: `aion path` on any machine with the branch checked out; first undone step is the resume point

---
Read next, in order: OWNER_README.md → docs/FINDINGS_LOG.md → incoming/README.md → `aion path`.
