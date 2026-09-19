# Secure Capability Gateway + Alternative-Path Engine
## Owner design review — research only

**Recommendation:** approve research/threat-model work only. Do not implement
the security-critical gateway until the trust model, cryptographic library,
device enrollment, approval protocol and abuse tests are independently
reviewed.

### 1. Current architecture

The intended first path is **iPhone/WhatsApp → provider webhook →
`bridges/whatsapp_bridge.py` → LucyOS router → canonical tasks/approvals/
workers**. OpenClaw is the agent/channel host and can invoke the existing
LucyOS integration/remote SSH path; LucyOS remains the governing state,
approval, capability and recovery system. Current runtime evidence says the
WhatsApp Cloud credentials and OpenClaw port are not configured, so this is
architecture, not a claim of live production connectivity.

### 2. Reuse before adding

Reuse webhook HMAC verification, sender allowlisting, message-id deduplication,
bounded payloads, redaction, canonical SQLite, `tasks`, `approvals`,
sessions/resume/checkpoints, skills/capability reports, LearnRepo, architecture
checks, health and the governor. Do not create a second queue, scheduler,
secret store, approval engine or daemon.

### 3. Placement

Place a channel-independent control gateway between transport adapters and the
existing router/task boundary. WhatsApp, ChatGPT/local UI, CLI, SSH and future
messengers become adapters that submit the same authenticated command envelope.
The gateway normalizes, authenticates, authorizes, deduplicates and either
returns a read-only result or creates a canonical LucyOS task.

### 4. Sender and device authentication

Phone number or account ID is an identifier, never sole authority. Enrollment
uses an out-of-band, short-lived owner challenge and a device public key.
Every device has a revocable ID, key version, owner binding and last-seen
metadata. Lost devices are revoked immediately; new enrollment requires the
existing owner approval path or local presence.

### 5. Encryption and local key handling

Sensitive envelopes use an authenticated modern envelope scheme selected after
LearnRepo/library review; do not invent cryptography. Private keys remain in
the OS secret store or existing protected secret provider, never SQLite,
WhatsApp, GitHub, prompts or ordinary logs. Key rotation keeps old keys only
for bounded decrypt/revocation windows. Provider transport TLS is necessary
but does not replace end-to-end envelope protection.

### 6. Explicit approvals and authorization

Approval signs the normalized action, arguments, target, capability version,
risk class, device ID, nonce and expiry. A changed action, target or argument
invalidates the approval. Reuse LucyOS approvals and owner gates; do not let a
channel reply such as “yes” authorize a different action than the displayed
summary.

### 7. Nonce, time and replay protection

Require unique device nonce, issued-at/deadline window, monotonic message ID
where available, canonical payload hash and durable idempotency key. Store only
minimal replay metadata in canonical state with retention/cleanup policy.
Duplicate delivery returns the original task/result reference and never runs
the side effect twice.

### 8. Durable request conversion

After authentication and policy classification, a request becomes one existing
LucyOS task with source channel, authenticated device, payload hash, requested
capability, approval ID, risk class, evidence path and rollback requirement.
Workers claim and checkpoint it through existing task/session mechanisms.

### 9. Risk and owner gates

Read-only status/capability queries are lowest risk. Local reversible code or
task preparation is bounded risk. Credentials, network/firewall, public
exposure, external messages, spending, deletion, deployment and canonical
merges remain explicit owner-gated actions. The gateway cannot lower a task's
risk class or bypass the governor.

### 10. Capability discovery and alternatives

If a requested method is unavailable, return a structured explanation of the
missing capability, available safe alternatives, cost/data/security tradeoffs,
and exact owner action if needed. Examples: existing local model, Codex/SSH
path, configured skill, or LearnRepo research. Never silently install software,
switch providers, expose a port or broaden permissions.

### 11. LearnRepo integration

Capability gaps follow the existing NEED → SEARCH → QUEUE → VERIFY source,
license and security → SANDBOX → EXTRACT → TEST flow. External instructions
remain untrusted data. A research result proposes a capability; it does not
activate one.

### 12. Sandbox and promotion

Prototype in an isolated worktree/sandbox with synthetic credentials and no
production network or canonical state. Require deterministic tests, abuse and
replay tests, secret scan, portability/security review, cost/rollback evidence
and owner approval before promotion.

### 13. Capability lifecycle

`PROPOSED → EXPERIMENTAL → VERIFIED → OWNER_APPROVED → ACTIVE → DEPRECATED`.
Each transition records evidence, manifest/version, owner decision, scope,
risk/data class, executor, rollback and revocation path. Deprecated capability
IDs remain recognized for audit but cannot execute.

### 14. Credential and log handling

Secrets use existing SecretRefs/OS secret storage. Logs contain IDs, hashes,
risk and outcomes—not tokens, cookies, private keys, plaintext envelopes or
raw WhatsApp bodies. GitHub receives code, redacted evidence and design docs
only; secret scans are mandatory before push.

### 15. Recovery and revocation

Revoke device key/version, invalidate outstanding approvals and rotate affected
provider credentials through the existing owner-controlled process. Preserve
minimal audit evidence, mark in-flight tasks for review, and prevent automatic
retry under a revoked identity. Recovery must be idempotent after restart.

### 16. Smallest useful MVP and later phases

**MVP:** one channel adapter, one enrolled owner device, read-only capability
query, one bounded durable task-creation command, signed expiring approval,
nonce/replay protection, redacted audit result, and revocation tests.

**Later:** multiple adapters, encrypted sensitive payloads, alternative-path
ranking, LearnRepo proposal automation, capability experiments, rotation UX,
local-presence confirmation and richer recovery dashboards.

### Owner decision requested later

Approve only the threat-model/research phase first. Implementation needs a
separate architecture/security review and explicit owner approval after the
MVP protocol and cryptographic choices are evidenced.
