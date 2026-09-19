# SCG-01 dependency/security review

**Date:** 2026-09-19

## Selected runtime set

`pycose==1.1.0` (BSD-3-Clause), `cbor2==5.6.5`, `cryptography==41.0.7`,
`ecdsa==0.19.2`, `attrs==23.2.0`, `certvalidator==0.11.1`,
`asn1crypto==1.5.1`, `oscrypto==1.3.0`, `cffi==1.16.0`, and
`pycparser==2.22`. Direct and transitive versions are pinned in
`requirements-gateway.txt`. The selected CBOR version preserves Python 3.9
compatibility; newer cbor2 releases require Python 3.10+.

## Review result

- COSE_Sign1 Ed25519 interoperability was exercised with `pycose` and the
  existing `cryptography` provider: encode, decode and signature verification
  passed in an isolated wheel environment.
- Python 3.12/Linux wheel import passed. CI installs the same pinned manifest;
  the repository’s supported matrix remains Python 3.9/3.11/3.13.
- No GPL dependency was selected. `cwt` was rejected because it requires
  Python 3.10+ and adds HPKE outside Phase 1. Custom COSE/CBOR was rejected.
- No `pip-audit`, `osv-scanner` or `trivy` binary is installed on Lucy-den;
  therefore the OSV API was queried directly for each pinned package on
  2026-09-19. The result is **NOT CLEAR**: OSV reports affected advisories for
  `cbor2==5.6.5`, `cryptography==41.0.7` and `ecdsa==0.19.2`; it reports no
  matching advisories for pycose, certvalidator, oscrypto or asn1crypto.
  The vulnerable packages are not accepted as an activation-ready dependency
  set. Some findings concern code paths not used by Ed25519, but that is not a
  sufficient reason to claim a clean supply-chain gate.
- Newer cbor2 releases require Python 3.10+, while pycose brings ecdsa as a
  runtime dependency. Resolving this safely requires either a maintained COSE
  implementation with a clean current dependency graph or an owner-approved
  retirement of Python 3.9 support; neither is silently assumed.
- No private keys, payload secrets or credentials are included in the manifest,
  tests, evidence or logs.

References: RFC 9052, pycose project metadata/license, cbor2 project metadata,
and the project’s approved `SCG-01` architecture decision.
