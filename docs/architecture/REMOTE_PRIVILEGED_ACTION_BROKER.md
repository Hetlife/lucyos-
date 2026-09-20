# REMOTE PRIVILEGED ACTION BROKER — architecture backlog design

Status: DESIGN ONLY / NOT IMPLEMENTED / NOT ACTIVATED
Canonical task: TASK-9AABB572

Goal: permit narrowly typed privileged Lucy-den actions without transmitting a sudo password or exposing arbitrary root execution.

## Security invariant
A compromised LLM, WhatsApp message, prompt injection, ordinary LucyOS process, or SCG client must never obtain a general root shell or a user-controlled exec primitive.

Forbidden surfaces include arbitrary sudo commands, arbitrary shell input, user-supplied exec strings, generic argv forwarding, caller-selected script paths, package-manager option passthrough, or service names outside a root-owned allowlist.

## Authority flow
WhatsApp / Codex -> Secure Capability Gateway -> existing LucyOS authority/governor -> exact signed approval -> local privileged broker -> deterministic typed operation -> independent verification -> existing durable evidence/checkpoint -> canonical task continuation.

The broker is an executor only. It owns no task state, queue, scheduler, retry engine, approval ledger, device registry, or policy authority. Mark-2 remains canonical task authority; SCG/device enrollment remains the authentication and exact-operation boundary.

## Request binding
Every request must bind exactly: action, canonical parameters, target machine, request/task ID, risk class, enrolled device identity/key epoch, nonce, expiry, policy version, and signature.

The broker independently revalidates action, parameters, target, expiry, nonce/receipt, and policy version before privileged execution. No LLM output is trusted as executable input.
## Initial typed capabilities
- `system.package.install(package=<validated allowlisted package>)`
- `system.service.restart(service=<allowlisted service>)`
- `system.service.status(service=<allowlisted service>)`
- `runtime.provision(spec=<validated bounded runtime spec>)`

Each capability has its own parameter schema and root-owned allowlist. No capability accepts shell syntax, environment overrides, arbitrary file paths, package-manager flags, unit-file fragments, or executable names from the caller.

## Linux implementation options
### A. Root-owned broker service + Unix socket — preferred pilot
A minimal root-owned service receives a fixed schema over a local Unix-domain socket. Filesystem/socket permissions limit callers. The service validates the SCG-approved envelope again and executes internal typed handlers with fixed absolute binaries and fixed argument construction.

Harden with the smallest filesystem view and capability set, restricted address families, private temporary storage, explicit writable paths, and systemd security controls. Sensitive broker verification material should use root-owned files or systemd credentials rather than environment variables.

Advantages: strongest separation from the unprivileged LucyOS/LLM process; deterministic API; straightforward audit receipts; clean emergency stop by disabling one root-owned service/socket and revoking its policy epoch.
Tradeoff: installing the service is itself a privileged owner-gated action and needs a macOS host adapter later.

### B. Narrow sudoers wrapper
If used, grant passwordless execution only to one root-owned immutable broker executable. Never grant package managers, service managers, shells, interpreters, editors, or directories directly. The wrapper must parse typed data itself and reject arbitrary argv.
### C. polkit-authorized system service
Expose explicit privileged methods from a system service and let polkit authorize fixed action IDs. Polkit can add useful local desktop authorization, but its rules must not become a second LucyOS approval engine.

Advantages: native Linux authorization model and good desktop integration.
Risks: additional policy surface; remote signed LucyOS approval still needs broker-side validation. Treat polkit only as an OS authorization layer.

### D. Linux capabilities without root
Use file or ambient capabilities only when one narrow kernel capability truly covers an operation. This can reduce privilege for future single-purpose handlers, but it does not safely cover general package installation or service management.

## Recommendation
Pilot A: a tiny root-owned broker with a local Unix socket and fixed typed handlers. Installation and activation remain separate owner gates. If bootstrap needs sudoers, permit only the immutable broker installer/control binary with exact semantics; never expose direct package-manager or service-manager authority.

Polkit is optional for local interactive authorization. Linux capabilities should be preferred later wherever they can eliminate root for a specific handler.

## macOS compatibility
Keep the capability protocol OS-neutral. Implement the macOS privileged executor as a host adapter using Apple's Service Management model. On macOS 13+, `SMAppService` manages approved LaunchDaemons; Apple documents LaunchDaemons as root background processes that require admin approval. Do not port Linux sudoers or polkit assumptions to macOS.

## Broker-side fail-closed validation
Before an operation, require: valid enrolled-device signature/key epoch; exact locally registered action; exact allowed fields and values; matching machine identity; matching task/request approval; compatible risk class; unused nonce; valid expiry; exact locally installed policy version; exact parameter hash; and non-revoked capability.

The broker constructs process arguments internally from constants and validated enums/tokens. It never invokes a shell.
## Verification and durable evidence
Every operation returns a structured receipt containing request ID, task ID, capability/version, parameter hash, device/key epoch, broker policy version, timestamps, deterministic exit status, bounded/redacted result, independent verification result, and broker build identity.

The caller stores that through existing LucyOS evidence/checkpoint paths. The broker does not create a second canonical ledger.

Postconditions are capability-specific: package installs verify installed package/version; service restarts verify the allowlisted unit state; status is read-only typed output; runtime provisioning verifies declared artifacts/checksums/permissions.

## Emergency revocation
Owner-visible operation: `REVOKE REMOTE PRIVILEGED AUTHORITY`.

The local emergency path must work without cloud, WhatsApp, or an LLM. It disables the broker activation path, revokes/rotates the accepted policy/key epoch, closes the broker socket, disables SCG privileged capabilities, and preserves audit evidence. Re-enable requires a fresh local owner gate.

## Required hostile tests before activation
- prompt injection cannot alter action or parameters;
- shell metacharacters, extra argv fields, path traversal and symlink attacks are rejected;
- package/service allowlist bypasses are rejected;
- stale/replayed, expired, wrong-device, wrong-target and wrong-policy requests fail closed;
- an unprivileged LucyOS process cannot invoke unapproved privileged work;
- broker filesystem/network access is bounded;
- failures do not create a new retry authority;
- emergency revoke works offline;
- private keys and secrets never enter logs, argv, Git, WhatsApp, or task evidence.
## Rollout gates
G0 design/research only — current state.
G1 owner approves implementation architecture.
G2 build helper in an isolated branch; hostile tests; no privileged install.
G3 independent security review plus architecture/authority gates.
G4 owner approves one local privileged installation action.
G5 read-only `system.service.status` pilot.
G6 one harmless reversible privileged action on an explicit target.
G7 only then consider package/runtime capabilities individually.

No gate implies approval of a later gate.

## Research basis
- sudoers(5): command specs can bind fully qualified commands and arguments; omitting arguments permits arbitrary arguments. https://www.sudo.ws/docs/man/1.9.14/sudoers.man.pdf
- polkit reference: authorization checks use action IDs/subjects; rules are administrator policy. https://polkit.pages.freedesktop.org/polkit/polkit.8.html
- systemd.exec: privilege, capability-bounding and service sandbox controls. https://github.com/systemd/systemd/blob/main/man/systemd.exec.xml
- systemd credentials: service-scoped credential acquisition avoids ordinary environment-variable propagation. https://systemd.io/CREDENTIALS/
- Apple Service Management: `SMAppService` controls LaunchAgents/LaunchDaemons subject to user/admin approval. https://developer.apple.com/documentation/servicemanagement/smappservice

## Owner gate before implementation
The proposed Linux pilot is a root-owned deterministic broker service over a local Unix socket, reusing existing SCG exact signed approvals and existing LucyOS state/evidence. This document installs, enables and grants nothing. Implementation and privileged activation remain separate gates.