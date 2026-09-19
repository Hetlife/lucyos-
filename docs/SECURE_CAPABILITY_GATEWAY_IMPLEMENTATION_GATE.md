# Secure Capability Gateway — Phase-1 Implementation-Ready Owner Gate

**Status:** implementation-ready design; implementation and deployment are not
approved by this document. **Decision: APPROVE DESIGN / REQUEST SEPARATE
IMPLEMENTATION APPROVAL.**

This specification resolves the open protocol, enrollment, approval, threat,
and abuse-test questions for the existing Secure Capability Gateway epic. It
does not create a daemon, queue, executor, or parallel authority plane.

## Recommendation

Use **COSE_Sign1 (RFC 9052)** with **EdDSA/Ed25519** for the canonical
approval envelope. Use the maintained Python `cryptography` package for
Ed25519 key generation/signing/verification and OS-backed key storage; use a
small, maintained COSE implementation only after dependency review confirms
its current release, license and test posture. The wire format is standard
COSE, not a LucyOS-proprietary cryptographic protocol.

Phase 1 deliberately does **not** encrypt arbitrary command payloads. Incoming
natural language, attachments and secrets remain untrusted and are rejected or
redacted by existing security policy. Transport/provider TLS and webhook
authentication remain in place. If a later requirement needs confidential
payloads, use an independently reviewed standard HPKE (RFC 9180) or age
envelope after a separate design gate; never invent an encryption format and
never use encryption-key possession as authorization.

Rationale: COSE_Sign1 gives a standard canonical signature structure and
algorithm agility; Ed25519 is directly supported by `cryptography`. X25519 and
ChaCha20-Poly1305 are available for a later confidentiality layer, but adding
them now would increase key lifecycle and payload-handling risk without being
needed for the smallest useful MVP. The `cryptography` project documents
Ed25519, X25519 and ChaCha20-Poly1305 support and uses an Apache-2.0/BSD-3-
Clause license. RFC 9052 defines COSE_Sign1; RFC 9180 defines HPKE.

Rejected for Phase 1:

- custom JSON signing/encryption: canonicalization and algorithm handling would
  become LucyOS security code;
- HMAC-only device authentication: shared secrets cannot identify/revoke a
  device independently and do not provide asymmetric approval signatures;
- JWT/JWS: workable, but larger textual tokens and a second serialization/key
  profile are unnecessary when COSE is designed for compact signed objects;
- a new gateway daemon or queue: duplicates OpenClaw ingress and LucyOS tasks;
- passkeys/WebAuthn as the first executor protocol: promising for interactive
  device enrollment, but adds browser/platform ceremony; it may be a future
  enrollment adapter, not a reason to enlarge Phase 1;
- age/HPKE now: appropriate for later confidential payloads, not needed when
  Phase 1 rejects secrets and only signs exact operations.

## Trust boundaries and data flow

```
WhatsApp/CLI/UI adapter (untrusted content)
  -> provider/webhook authentication + bounded parsing + adapter dedup
  -> channel-neutral envelope validation (COSE/signature/device/replay)
  -> LucyOS security.redact + risk/governor + existing owner approval policy
  -> existing canonical task + session/checkpoint/resume state
  -> existing bounded allowlisted executor
  -> redacted evidence/result
  -> adapter response
```

OpenClaw owns channel ingress, UX and tool surfaces. LucyOS owns canonical
authority, policy, approvals, tasks, checkpoints, capabilities and recovery.
No adapter may grant authority, turn text into shell, or bypass the governor.
Natural-language text, attachments, provider metadata and LearnRepo material
are data, never policy. Possession of a phone, transport token, signing key or
encryption key is necessary-but-not-sufficient: LucyOS policy and the exact
approval still decide authority.

## Enrollment, rotation and revocation

1. The owner starts `device-enroll` locally or through the existing owner-gated
   control surface. LucyOS creates a short-lived, single-use challenge with a
   random enrollment ID and expiry; it contains no secret.
2. The device generates an Ed25519 key in OS secure storage (hardware-backed
   storage where available). The private key never enters WhatsApp, GitHub,
   task text or ordinary logs.
3. The device presents device ID, public key, platform label and challenge
   proof through the authenticated adapter. The owner confirms the displayed
   fingerprint out of band. LucyOS records the public key, key version,
   enrollment epoch, status and owner confirmation in existing canonical state.
4. Multiple active devices are supported. Each has an independent key and
   policy record. A device key signs requests/approvals but cannot approve an
   operation that policy does not permit.
5. Rotation creates a new key version and invalidates the old version after
   explicit owner confirmation. Revocation is immediate, increments the device
   epoch, invalidates outstanding approvals and prevents task creation from the
   old key.
6. Lost/replaced device recovery is owner-controlled from a remaining trusted
   device or local recovery path. If no trusted device remains, require local
   host recovery; do not recover through an unauthenticated WhatsApp message.

## Canonical approval object

The application payload carried as the COSE_Sign1 payload is a versioned,
canonical CBOR map. The exact operation digest is calculated over the canonical
CBOR encoding of the following required fields, with no omitted defaults:

```text
{
  schema:       "lucyos.approval/1",
  request_id:   immutable unique request/task identifier,
  action:       exact registered capability/action name,
  params_hash:  SHA-256(canonical CBOR of validated parameters),
  target:       exact logical target or null,
  risk_class:   policy risk class,
  capability:   immutable capability/version identifier,
  device_id:    enrolled device identifier,
  key_version:  enrolled signing-key version,
  identity:     owner identity subject,
  nonce:        cryptographically random single-use value,
  issued_at:    UTC timestamp,
  expires_at:   UTC timestamp with bounded maximum lifetime,
  policy:       policy identifier and monotonic policy version,
  approval_id:  unique approval identifier,
  epoch:        current device/authority revocation epoch
}
```

The COSE protected headers identify the algorithm (`EdDSA`), schema/content
type and key ID. The signature covers the complete canonical payload and the
request context. Materially changed action, target, parameters, risk,
capability, device, policy or expiry requires a new approval and nonce.

Validation order is fail-closed: decode/type limits -> schema/version -> time
window/skew -> enrolled key and epoch -> signature -> canonical digest ->
policy/risk -> durable nonce/idempotency claim -> existing task/approval
transition. A valid signature alone never bypasses policy.

## Phase-1 files and reused modules

Implementation should be limited to:

- extend `aion_core/approvals.py` and the existing SQLite migration mechanism
  with signed-envelope fields, device/key status, nonce claim and exact digest;
- add one small channel-neutral validator adjacent to the existing router,
  reusing `aion_core/security.py`, `governor.py`, `tasks.py`, `resume.py`,
  `db.py`, and existing capability/skill manifests;
- adapt `bridges/whatsapp_bridge.py` to submit validated envelopes rather than
  authorize directly; preserve provider HMAC, sender filtering and message-ID
  dedup;
- add enrollment/revocation commands through existing owner-gated interfaces;
- add focused security/replay/idempotency and one synthetic second-adapter
  test harness.

No new daemon, queue, database, arbitrary-shell endpoint, secret store,
capability registry, or executor is in scope. Use the existing SecretRef/OS
secret-storage mechanism for host-side secrets. No private key or payload
secret is persisted in GitHub, WhatsApp history, normal logs or evidence.

## Compatibility and migration

Existing approval rows remain readable. Legacy unsigned approvals are marked
`legacy` and cannot authorize a new remote/device request; existing local owner
flows may finish only under the current policy and are not silently upgraded.
New requests require schema version 1 and a device record. Database migration
is additive and idempotent, with a feature flag defaulting to deny remote
execution until enrollment and validation are configured. Rollback disables
the feature flag and restores the previous adapter path for read-only/status
traffic; it must not reactivate revoked keys or execute queued actions.

## Abuse and acceptance matrix

| Case | Expected result |
|---|---|
| valid enrolled device, exact low-risk request | one durable task, one checkpoint/evidence record |
| replayed envelope or nonce | reject; no second task; redacted audit event |
| duplicate webhook/message ID | return original result/task reference; no execution |
| changed parameters after approval | digest mismatch; reject and require new approval |
| forged/invalid signature | reject before policy/task creation |
| expired or future-out-of-window approval | reject; no task |
| wrong or revoked device/key epoch | reject; invalidate matching outstanding approvals |
| malformed/oversized/unknown schema | reject before deep parsing; no secret log |
| risk escalation or capability substitution | governor denial; owner gate remains required |
| prompt injection in text/attachment/LearnRepo | treated as data; cannot alter policy or authority |
| malicious attachment/type bomb | quarantine/bound scan; never auto-execute |
| restart between approval and execution | durable idempotency claim resumes once or enters review |
| duplicate task-creation race | unique request/digest constraint yields one task |
| executor failure/partial side effect | checkpoint error, stop/review or safe resume; no blind retry |
| lost phone/stolen key | immediate revoke, epoch bump, approval invalidation, re-enroll |
| rollback to older policy/capability | monotonic version/epoch check rejects downgrade |
| compromised executor | bounded capability/worktree, evidence mismatch detection, stop/revoke |
| positive cross-adapter path | WhatsApp and synthetic CLI produce identical validation/task semantics |

Required gates: focused abuse matrix, positive end-to-end test, full suite,
`aion verify --json`, architecture audit, secret scan, portability, strict
scope, dependency/license review, restart/recovery and regression checks.

## Threat controls and residual risks

Spoofing, stolen phones/keys and compromised accounts are controlled by provider
authentication plus enrolled public keys, exact signatures, epoch revocation and
owner policy; detect with redacted rejection/audit events; recover by immediate
revocation and approval invalidation. Replay and duplicate delivery are
controlled by nonce, expiry, monotonic epoch, unique request/digest claims and
provider IDs; recover by marking the original task/result and requiring a new
approval. Tampering and malicious attachments fail signature/type/size/content
checks and are quarantined. Prompt injection and malicious LearnRepo content
remain untrusted data; source/license/security verification, sandboxing and
owner-approved lifecycle transitions are mandatory. Executor compromise,
partial failure, restart and rollback are bounded by existing capability
allowlists, worktree/checkpoint/recovery state, monotonic policy versions and
fail-closed review states. Leaked logs are mitigated by existing redaction and
secret scanning; affected credentials/keys are rotated. Residual risks include
provider-account compromise, host compromise, device unlock compromise and
cryptographic/dependency defects; Phase 1 does not claim to eliminate them.

## Scope explicitly excluded

No gateway implementation, production activation, public port, arbitrary shell,
credential transport, automatic installation, autonomous capability activation,
custom crypto, new daemon/queue/approval system, or canonical/main promotion.
The Alternative-Path Engine may propose supported alternatives and sandboxed
experiments only; it may never discover or suggest a security bypass.

## Exact owner implementation approval requested

Approve implementation of **only** the Phase-1 boundary in this document:
COSE_Sign1/Ed25519 signed exact-operation envelopes, OS-backed device-key
enrollment/revocation, additive approval/task validation fields, existing
LucyOS authority/task/checkpoint integration, WhatsApp as an adapter, bounded
executor invocation, redacted evidence, and the listed abuse tests. Approval
does not authorize deployment, public exposure, arbitrary shell, secret
transport, automatic capability activation, or changes to canonical/main;
those remain separate owner/protected gates.

## Research evidence

- IETF RFC 9052, COSE Sign1: https://www.rfc-editor.org/rfc/rfc9052.html
- IETF RFC 9180, HPKE (future confidentiality layer):
  https://www.rfc-editor.org/rfc/rfc9180.html
- `cryptography` asymmetric/key and AEAD documentation:
  https://cryptography.io/en/stable/
- Existing LucyOS review and reusable-boundary evidence:
  `docs/SECURE_CAPABILITY_GATEWAY_FINAL_REVIEW.md` and
  `docs/SECURE_CAPABILITY_GATEWAY_MVP.md`
