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

## F8 — No test/live signal on a payment link. **HIGH (found while building S09)**
`GET /api/v2/payment-links` returns `status`, `provider`, `provider_payment_id`
and amounts, but nothing indicating whether the configured Razorpay
credentials are test-mode or live-mode. `status=='paid'` is already
provider-reconciled inside SEVAA (`backend/revenue.py::_mark_paid` only flips
to `paid` after querying Razorpay), so S09 treats it as the verified signal —
that part is sound. The gap is narrower than it first looks: **if the founder
ever configures a Razorpay TEST key against a production-reachable
deployment**, a test payment would reach `paid` and AION would record it as
ACTUAL revenue and could flip M0. Until a real key is configured this cannot
happen (`get_razorpay_config()` returns `None` with no credentials, and no
paid status is reachable without a working provider config). **Not blocking**
S09: recorded here so the founder's own gate — never put test keys in a
production deployment once `/quote` is public — is the control, and so a
future SEVAA-side task can surface the key mode explicitly rather than relying
on operational discipline alone.

## S02 security review — Class A, recorded before merge

Reviewed: `aion_core/sevaa.py` (decide_approval, list_pending_approvals,
_require_safe_transport), `aion_core/approvals.py` (decide()'s external_ref
branch), `aion_core/resume.py` (_sync_sevaa_approvals), `aion_core/router.py`
(the PENDING-with-error reply path).

**Finding, fixed:** nothing stopped `SEVAA_BASE_URL` from being plain HTTP.
Since the founder token is the one credential in this whole integration that
can move a real proposal to approved, sending it in cleartext to a
non-loopback host would be the worst possible place for a gap. Added
`_require_safe_transport`: loopback keeps working over HTTP for local
development, anything else must be `https://` or the call refuses before a
socket opens. Applied to every call that carries a token (`_get`,
`decide_approval`). Tests: loopback HTTP allowed, non-loopback HTTP refused,
non-loopback HTTPS allowed, `daily_brief` surfaces the refusal as an
unreachable state rather than crashing.

**Checked, no change needed:**
- The founder token is read fresh inside `decide_approval` on every call —
  never cached, never logged, never placed in a value that reaches a report
  or the event log. Verified by a test that greps the entire event table
  after an approve/deny round trip.
- A second `APPROVE` on an already-decided card never reaches the network:
  `decide()` returns early on non-PENDING status before the external_ref
  branch runs. Verified by a 3x-replay test asserting exactly one HTTP call.
- A non-2xx or unreachable response leaves the card `PENDING`, never
  `APPROVED`— local state changes only after the remote call returns
  successfully. Verified with a mocked 409 and a mocked connection refusal;
  the second test also confirms a later retry can still succeed.
- SEVAA's own endpoint (`backend/phase2.py::decide_approval`) already
  rejects a decision on a non-pending approval with 409, so a race between
  two deciders is a server-side guard, not something AION needs to
  duplicate.
- `_sync_sevaa_approvals` reads `lead_name`/`lead_company` off the SEVAA
  response (present because `list_approvals`'s join includes them, a
  pre-existing SEVAA characteristic) and discards both — only
  `scope_summary` and `amount` reach the card. Verified against the card's
  actual `action`/`why` text with a deliberately identifying lead name in
  the mocked response.
- The sender-identity boundary for every WhatsApp command, S02's approve/deny
  included, is the `WHATSAPP_BRIDGE_TOKEN` checked once at the transport
  layer in `bridges/whatsapp_bridge.py`; there is no secondary per-message
  sender-number allowlist. This is existing architecture, not something S02
  introduces or weakens — pause, resume, safe mode and every other
  consequential command rely on the same boundary. Noted here rather than
  silently accepted: if the founder wants a second factor (e.g. only a
  specific WhatsApp number may approve), that is a new task, not a defect
  in this one.

**Verdict:** safe to merge. 184 tests pass; `aion scan .` clean.
