# 06 — Owner Decisions

Only decisions that a machine cannot make for you. Each has a recommendation; replying "accept all recommendations" is a valid answer.
Record your decision by editing the **Decision** line and committing, or by telling the next AI session, which will record it here.

## Required NOW (block Phase 0/1 work)

### OD-01 — Repository visibility
`Hetlife/lucyos-` and `Hetlife/strategy-factory` are public (verified 2026-09-16). History of `lucyos-` contains no credentials. It does contain your mission text, revenue targets and Upwork proposal drafts, and will contain business schemas.
**Recommendation:** make both private now. Cost: zero. Reversible. Exact action: GitHub → repo → Settings → General → Danger Zone → "Change repository visibility" → Private (repeat for strategy-factory). Optional: same for `paperclip` fork and `claude-test`.
**If you keep them public on purpose:** say so, and LQ-08 will add a guard that keeps `work/` and any business data out of git.
**Decision:** _pending_

### OD-02 — Hardware: buy nothing for now
**Recommendation:** no controller, GPU, dock or UPS purchase until the Phase-1 exit gate (≈60–90 days). Mark-2 stays the controller and is hardened. Re-decide with measured RAM/CPU, VPS bill, data classification and inference telemetry. If on-prem is then justified: fanless Linux mini-PC by default; Mac mini base model only if you prefer macOS.
**Decision:** _pending_

### OD-03 — Disable the root remote-shell service on Mark-2
`mark2-desktop-commander.service` gives a third-party relay root terminal/file access on the machine holding your canonical state and secret file.
**Recommendation:** disable now: `systemctl --user disable --now mark2-desktop-commander.service` on Mark-2, then approve LQ-11 to delete the unit from the repo. Remote admin afterwards = your own SSH key over Tailscale to a non-Lucy account (LQ-10 sets this up).
**Decision:** _pending_

### OD-04 — Spend caps (standing AMBER policy)
Current defaults: ₹200/day and ₹2,000/month model spend; ₹2,000 strong-model build cap; cloud GPU ₹0.
**Recommendation:** keep these for Phase 0–2; cloud GPU stays ₹0 until Phase 4; raise only after 30 days of telemetry.
**Decision:** _pending_

### OD-05 — Off-host backup destination
Needed to execute LQ-02.
**Options:** (a) DigitalOcean Spaces bucket (same provider as Mark-2 — simplest, weakest independence); (b) Backblaze B2 with object-lock (recommended: independent provider, append-only capable, ≈₹0–500/month at this size); (c) external disk at the office pulled by a scheduled job over Tailscale (needs an always-on office machine).
**Recommendation:** (b), plus keep DO weekly droplet images.
**Decision:** _pending_

### OD-06 — Approve the non-root migration maintenance window
LQ-10 changes the security boundary on Mark-2 (new `lucy` user, moved `AION_HOME`, per-service env files). It is RED by our own rules and must be run by you (or by a worker session you explicitly authorize for that window) with a pre-change backup taken first.
**Decision:** _pending_

## Can WAIT (LucyOS keeps building without them)

| ID | Decision | Default until decided |
|---|---|---|
| OD-07 | First production business workflow | Document intake for SEVAACONNECT (ADR-13) |
| OD-08 | Data classification per company/project (PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED) | Everything non-public = CONFIDENTIAL; nothing RESTRICTED yet |
| OD-09 | Identify the office Radeon PC (exact GPU, OS) and permit the qualification test | Not qualified; cloud APIs only |
| OD-10 | Telegram as second channel | Not built |
| OD-11 | WhatsApp template/pricing verification for business-initiated alerts | Owner-initiated conversations only |
| OD-12 | CRM / accounting platform to connect (Zoho, HubSpot, Tally, …) | None connected; schema mirrors only |
| OD-13 | Required recovery time after controller failure | 4 h RTO, 24 h RPO (ADR-11) |
| OD-14 | Which sessions/tools may act as class B/C workers (Codex, Claude Code, others) | Whatever is already configured via `aion set-cloud-cmd` |
| OD-15 | Postgres / Temporal / n8n adoption | Never, until ADR-03/04 triggers fire |
| OD-16 | Voice escalation provider | Not built |
| OD-17 | Any dropshipping/commerce pilot | Not started; unit-economics template only |
| OD-18 | Real-capital policy for Strategy Factory | Paper only; RED with no standing policy |
