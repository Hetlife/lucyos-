# SCG-01 — COSE_Sign1 dependency

**Status:** accepted for Phase 1 implementation; activation remains separately
gated.

## Decision

Use `pycose==1.1.0` for RFC 9052 COSE_Sign1 structures, `cbor2==5.6.5` for
canonical CBOR, and the existing `cryptography` provider for Ed25519. Pin the
direct and transitive runtime set in `requirements-gateway.txt`; CI installs it
before compile/tests. The normal LucyOS install remains safe to rerun and does
not activate the gateway.

`cbor2` is constrained below 6 because its current release line requires
Python 3.10 while LucyOS still tests Python 3.9. The selected 5.x line is the
compatibility floor for the supported matrix. Re-evaluate the constraint when
Python 3.9 is retired.

## Evidence and trade-off

`pycose` is a production/stable Python COSE implementation, BSD-3-Clause, and
supports the project’s Python 3.9+ range. It delegates cryptographic operations
to `cryptography` and uses CBOR rather than introducing a proprietary wire
format. Its dependency surface includes `cbor2`, `ecdsa`, `attrs` and
`certvalidator`; these must remain pinned and scanned. No optional encryption
feature is enabled by this decision.

`cwt` was rejected for Phase 1 because it requires Python 3.10+, brings an
additional HPKE dependency, and exceeds the smallest signed-envelope scope.
GPL-licensed COSE alternatives were rejected for licensing fit. Hand-writing
COSE/CBOR was rejected because it would create security-critical serialization
code inside LucyOS.

## Security conditions

- CI and clean bootstrap install from the pinned manifest only; a future
  artifact-lock step should add platform-specific hashes before activation.
- Dependency metadata, licenses and known-vulnerability scan are required
  before merge; a failing scan blocks implementation.
- Decode is bounded and fail-closed before signature/policy evaluation.
- Ed25519 private keys remain in OS/SecretRef storage; no private key or secret
  payload is serialized by COSE or stored in logs.
- This decision authorizes signed approvals only; it does not authorize
  sensitive-payload encryption, arbitrary shell, deployment or activation.
