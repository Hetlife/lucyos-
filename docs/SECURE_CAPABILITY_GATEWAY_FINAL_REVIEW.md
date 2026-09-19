# Secure Capability Gateway — Final Pre-Implementation Review

**Decision: REVISE**

The direction is compatible with LucyOS, but implementation must wait for a
revised Phase-1 protocol. The current system has transport HMAC, sender
allowlisting, redaction, deduplication, canonical tasks and owner approvals;
it does **not** yet have device-bound authorization or approvals cryptographically
bound to action parameters, risk, expiry and nonce. Treating the existing
approval row or WhatsApp sender as sufficient would be unsafe.

## Architecture and trust boundaries

`channel adapter → authenticated request envelope → channel-independent gateway
→ LucyOS security/risk/approval checks → canonical task/session/checkpoint
→ bounded existing executor → redacted evidence/result → adapter`.

OpenClaw owns ingress, UX and tool surfaces. LucyOS owns canonical state,
tasks, approvals, governor, skills, LearnRepo, architecture checks and resume.
WhatsApp is only an adapter; possession of a phone, WhatsApp account, transport
token or encryption key is never unlimited authority.

## Required reuse

Reuse `bridges/whatsapp_bridge.py` signature verification, sender filtering and
message-id deduplication; `aion_core/security.py` scanning/redaction; canonical
`db`, `tasks`, `approvals`, `resume`/sessions, governor, skills/capability
reports, LearnRepo and OpenClaw's existing LucyOS integration. No second queue,
approval engine, secret store, scheduler or executor boundary.

## Phase-1 proposed files/modules (design boundary only)

No implementation is approved by this review. The smallest proposed change set
for a later, separately approved implementation is:

- extend existing `aion_core/approvals.py`/canonical schema with a versioned
  normalized action digest, device ID/key version, risk class, nonce, issued/
  expiry times, approval signature/reference, status and revocation reason;
- add a small channel-neutral request-validation seam adjacent to the existing
  router, reusing `security`, `tasks`, `approvals`, `governor` and `resume`;
- adapt `bridges/whatsapp_bridge.py` to submit the envelope, never authorize
  directly;
- add focused security/replay/idempotency tests and redacted evidence only.

Do not add a new daemon, database, queue, crypto protocol, capability registry
or arbitrary shell endpoint in Phase 1. Capability lifecycle should initially
reuse existing skill manifests/registry; extend only after an architecture
review proves a missing field.

## Threat review

| Threat | Prevention | Detection | Recovery/revocation | Residual risk |
|---|---|---|---|---|
| spoofed sender | provider signature + enrolled device key; phone is not authority | rejected-signature/device events with IDs only | revoke device/key; invalidate approvals | provider/account compromise |
| stolen phone | device key + explicit approval; no phone-number authority | device/session anomaly and approval audit | revoke device; review tasks | unlocked device until revocation |
| compromised WhatsApp account | end-to-end request signature and device binding | failed signature/nonce/device checks | revoke device, invalidate approvals, rotate provider secret | provider metadata exposure |
| stolen device key | OS secret storage, key version, bounded enrollment | unknown key/version and anomaly events | immediate key/device revoke and re-enroll | host compromise |
| replayed approval | nonce, payload digest, issued/expiry window, durable idempotency | replay counter/status | mark request consumed; cancel stale task | clock/retention errors |
| modified ciphertext/request | authenticated encryption/signature over canonical bytes | MAC/signature failure | discard; no task creation | crypto/library defect |
| malicious attachment | type/size quarantine, no automatic execution, content scan | quarantine/audit result | delete/quarantine and revoke task | novel parser exploit |
| duplicate webhook/message | provider ID + canonical idempotency key | duplicate response reference | return original task/result; never execute twice | provider ID collision |
| privilege escalation | capability allowlist, risk policy, governor and owner approval | policy mismatch/audit gate | deny/cancel; investigate | policy omission |
| prompt injection | treat message/attachment/LearnRepo output as untrusted data; fixed policy outside payload | injection tests and policy violations | discard/quarantine; no authority change | model misinterpretation |
| malicious LearnRepo dependency | source/license/security verification, sandbox, no auto-activation | provenance and test evidence | quarantine proposal; revoke capability | supply-chain compromise |
| compromised executor | bounded executor class, worktree, least privilege, checkpoints | health/test/evidence mismatch | stop task, revoke capability, restore checkpoint | host-level compromise |
| leaked logs | redact before persistence/output; IDs/hashes only | secret scan and log audit | rotate affected secret/key; purge per retention policy | side-channel metadata |
| rollback attack | monotonic capability/version and approval epoch; protected baseline | version regression check | refuse old version; owner recovery | state-store compromise |
| gateway/OpenClaw restart | durable task/checkpoint/idempotency state; resume only valid tasks | boot health and stale-claim checks | requeue safely or mark review; no duplicate side effect | partial external side effect |

## Phase-1 acceptance criteria

1. Canonicalization produces one stable digest for action + parameters + target
   + capability version + risk class.
2. Missing, malformed, modified, expired, revoked, wrong-device, wrong-risk,
   reused-nonce and duplicate requests fail closed without task creation or
   secret-bearing logs.
3. Accepted low-risk request creates exactly one existing LucyOS task with
   source/device/digest/approval references and survives restart.
4. Consequential actions still produce existing owner approval cards and cannot
   be approved by a different action or altered parameters.
5. Bounded executor runs only an allowlisted capability in an isolated scope;
   result/checkpoint is redacted and auditable.
6. Device enrollment, rotation and immediate revocation are tested, including
   lost phone/key and outstanding approvals.
7. WhatsApp, CLI and a synthetic second adapter pass the same gateway tests.
8. Threat, replay, duplicate, prompt-injection, malicious-attachment,
   rollback, restart and partial-failure tests pass; full LucyOS gates remain
   green; no credentials enter GitHub or ordinary logs.

## Capability discovery and alternatives

The Alternative-Path Engine may search only for supported, policy-compliant
paths. It can report local/Codex/SSH/skill/LearnRepo alternatives with cost,
data and risk tradeoffs. It must never propose disabling auth, weakening a
gate, exposing a port, bypassing approval, installing silently or treating a
missing capability as permission to improvise.

Candidate lifecycle remains:
`PROPOSED → EXPERIMENTAL → VERIFIED → OWNER_APPROVED → ACTIVE → DEPRECATED`.
Each transition stores redacted evidence, provenance, version, risk/data class,
owner decision and rollback/revocation reference.

## Owner decision required

**Approve or reject only the Phase-1 design/research boundary.** Before code,
the owner must approve the threat model, cryptographic library/protocol choice,
device-enrollment flow, approval schema changes and test plan. Security/
architecture review is required again before activation or external exposure.

**Rollback:** design-only documents can be reverted. Any later implementation
must be isolated, feature-gated, reversible, and separately owner-approved.
