# SCG-01 — COSE_Sign1 dependency

**Status:** accepted for Phase 1 implementation; activation remains separately
gated.

## Decision

Use `scitt-cose==0.3.0` for RFC 9052 COSE_Sign1 structures, `cbor2==5.9.0`
for canonical CBOR, and `cryptography==50.0.1` for Ed25519. Pin the direct
runtime set in `requirements-gateway.txt`; CI installs it before compile/tests.
The normal LucyOS install remains safe to rerun and does not activate the
gateway.

`cbor2==5.9.0` retains Python 3.9 compatibility and has no matching OSV
advisory in the direct query performed for this gate. `cryptography==50.0.1`
also supports the current Python floor and has no matching OSV advisory.

## Evidence and trade-off

`scitt-cose` is Apache-2.0, supports Python 3.9+, implements COSE_Sign1 using
only `cbor2`, `cryptography` and the standard library, and includes strict
malformed-input handling. It avoids pycose’s unfixable `ecdsa` runtime
dependency. No optional encryption feature is enabled by this decision.

`pycose` was rejected after OSV review because its runtime graph includes
`ecdsa` with no fixed version for the reported advisory. `cwt` was rejected
because it requires Python 3.10+ and adds HPKE outside Phase 1. GPL-licensed
COSE alternatives were rejected for licensing fit. Hand-writing COSE/CBOR was
rejected because it would create security-critical serialization code inside
LucyOS.

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
