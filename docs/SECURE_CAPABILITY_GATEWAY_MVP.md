# Secure Capability Gateway + Alternative-Path Engine

**Phase:** research/design only; no implementation approved.

## Existing path and reusable capabilities

Current LucyOS already provides a transport boundary in
`bridges/whatsapp_bridge.py`: Meta webhook signature verification, single-owner
sender allowlisting, message-id deduplication, bounded payloads, redacted
replies, canonical router dispatch, and Cloud API credential loading from the
environment. The OpenClaw integration provides `lucyosctl`, remote SSH
enrollment scripts, context/health/task/approval commands, and a policy that
LucyOS remains the canonical state/approval/task system.

Reusable LucyOS seams are `security.redact`/secret scanning, canonical SQLite
tasks and approvals, sessions/resume/checkpoints, skill manifests and
availability reports, LearnRepo queue/status, architecture checks, and the
existing governor. No second queue, approval engine, secret store, or gateway
should be created.

Current evidence: OpenClaw is not configured in `aion health --deep`; WhatsApp
Cloud credentials are unset. The transport code exists but is not a live
authenticated production path on this checkout.

## Trust model

1. **Transport authenticity:** provider webhook signature and replay-resistant
   message ID; network endpoint private/tunneled, never public ad hoc.
2. **Device enrollment:** owner enrolls a device through an out-of-band,
   short-lived challenge; device key is public-key based and revocable. No
   phone number alone is authority.
3. **Message confidentiality:** encrypted envelope for sensitive commands;
   plaintext secrets never enter WhatsApp, logs, prompts, Git, or task state.
4. **Approval authenticity:** approval binds owner/device, exact normalized
   action, target, expiry, nonce, and risk class; replay and edits invalidate
   it. High-risk actions require a second confirmation or local presence.
5. **Execution boundary:** only existing allowlisted capabilities become
   durable tasks; shell/network/credential/firewall/public-exposure actions
   remain separately gated.

## Alternatives

- **Extend current bridge:** smallest MVP; reuse signatures, allowlist, dedup,
  router, tasks and approvals. Recommended if encrypted envelope and device
  enrollment are added without a new daemon.
- **Tailscale/VPN + SSH/Codex:** strong operator path for terminal work, but
  poor for structured approvals and capability discovery; complementary, not a
  replacement.
- **New gateway daemon/service:** clearer isolation but duplicates runtime,
  queue, secret and health concerns; reject for MVP.
- **Third-party automation platform:** faster integration but expands trust and
  data exposure; reject until threat model and licensing review.

## Smallest evolvable MVP

1. Offline threat model and data-flow diagram.
2. Device enrollment/revocation records using existing canonical approvals/
   state, with encrypted one-time enrollment payloads.
3. One read-only capability query and one durable task-creation command.
4. Owner approval envelope with expiry/nonce/idempotency; no arbitrary shell.
5. Alternative-path response that reports existing local/Codex/SSH/LearnRepo
   capabilities without auto-installing or escalating authority.
6. Security tests: replay, tampering, wrong device, duplicate delivery,
   redaction, expiry, downgrade, and malformed payloads.

## Research path and gates

Use LearnRepo for NEED → SEARCH → QUEUE → VERIFY source/license/security →
SANDBOX → EXTRACT → TEST. First research topics: modern device-bound passkey
enrollment, envelope encryption/key rotation, replay-resistant approvals, and
WhatsApp provider webhook limitations. Implementation requires an owner gate
after the trust model, smallest MVP, threat model, and independent security /
architecture review are accepted.
