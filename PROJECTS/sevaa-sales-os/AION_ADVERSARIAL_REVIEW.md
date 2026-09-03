# ADVERSARIAL REVIEW — SEVAA Sales OS + AION, 2026-09-03

Ranked by how much each would cost if left alone.

## F1 — A real enquiry is stored silently. Nobody is told. **CRITICAL**
`backend/public_enquiry.py:create_public_enquiry` inserts the lead and returns `{"accepted": true}`. No notification, no webhook, no event. The founder learns of their first real lead only by opening the console. The system's whole thesis — first genuine enquiry → paid pilot — has a hole at its first step. **Fix: S01.** Confidence 95%, reversible, ₹0.

## F2 — Founder approval requires the console; the founder has a phone. **HIGH**
Proposal decisions and payment links are founder-only (correct) but reachable only via the web console with a Bearer token. AION already has WhatsApp approval cards with unique ids, strict `APPROVE <ID>` form and replay safety. **Fix: S02.** Security condition: the founder token never leaves the PC's 0600 secret store; the bridge runs on the PC.

## F3 — Two "mission" systems, no bridge between them. **HIGH**
SEVAA counts enquiries/pilots/cash in `state/STATE.json`; AION counts milestones M0–M6 from `finance` rows. A verified Razorpay payment would update SEVAA and leave AION's M0 unreached. **Fix: S09** — payment reconciliation writes an ACTUAL revenue row with the payment id as evidence.

## F4 — PII would leak into WhatsApp if F1 is fixed carelessly. **HIGH (latent)**
A naive notification would put a lead's phone/email into a third-party chat app, contradicting `/privacy` and DPDP posture. **Constraint on S01/S07:** notifications carry lead id, score, city, requirement summary, source — never name, phone or email. Tests must assert it.

## F5 — 10 remote branches carry commits not in `main`. **MEDIUM**
`feat/privacy-pilot-hardening` (21 ahead), `feat/sevaa-postgres-*` (6–7 ahead), and six chore/agent branches. Most are squash-merged (same tree) but nobody has verified which. Dangling branches invite an agent to "finish" deferred Postgres work that T300 explicitly defers. **Fix: S04** — verify by tree, delete merged, tag deferred.

## F6 — Source attribution is asserted, not proven. **MEDIUM**
T102's acceptance says a real lead must be "source-attributed", but nothing shows `/quote?src=…` reaches `leads.source`. If it does not, T104 economics cannot be computed. **Fix: S06** — test it; add it if missing.

## F7 — The directive's read-first files do not exist in the SEVAA repo. **LOW**
`START_HERE_FOR_AI.md`, `AION_*.md`, `AGENT_TASKS.json`, `MACHINE_HANDOFF.json` are missing there. Every new agent will waste a search. **Fix: S05** — thin pointers, no duplicated prose.

## What is *not* wrong (checked, so nobody re-checks)
- No paid model calls in runtime. Cost strategy is already ₹0 by construction.
- No secrets in source. Razorpay/tokens are env-only.
- Automation credentials cannot approve; tested.
- Public enquiry is duplicate-safe and honeypot-protected.
- Backups are integrity-checked with a restore round-trip test.
- Deployment verifier is non-mutating and regression-covered.
- Nothing sends outbound messages autonomously. Keep it that way.

## Overbuild traps to refuse
Postgres (T300), multi-tenant (T202), AI provider layer (T203), paid ads, Kubernetes. All deferred by the SEVAA queue's own selection rule; the review agrees.
