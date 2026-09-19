# SCG-01 dependency/security review

**Date:** 2026-09-19

## Selected runtime set

`scitt-cose==0.3.0` (Apache-2.0), `cbor2==5.9.0`, and
`cryptography==50.0.1`. Direct versions are pinned in
`requirements-gateway.txt`. The selected CBOR version preserves Python 3.9
compatibility; newer cbor2 releases require Python 3.10+.

## Review result

- COSE_Sign1 Ed25519 interoperability was exercised with `scitt-cose` and
  `cryptography`: encode, decode and signature verification
  passed in an isolated wheel environment.
- Python 3.12/Linux wheel import passed. CI installs the same pinned manifest;
  the repository’s supported matrix remains Python 3.9/3.11/3.13.
- No GPL dependency was selected. `pycose` was rejected because its runtime
  graph includes `ecdsa` with no fixed version for the reported advisory.
  `cwt` was rejected because it requires Python 3.10+ and adds HPKE outside
  Phase 1. Custom COSE/CBOR was rejected.
- No `pip-audit`, `osv-scanner` or `trivy` binary is installed on Lucy-den;
  therefore the OSV API was queried directly for each pinned package on
  2026-09-19. The replacement result is **CLEAR**: OSV reports no matching
  advisories for `scitt-cose==0.3.0`, `cbor2==5.9.0` or
  `cryptography==50.0.1`. The replacement preserves Python 3.9 and removes
  the unfixed ecdsa runtime dependency.
- No private keys, payload secrets or credentials are included in the manifest,
  tests, evidence or logs.

References: RFC 9052, scitt-cose project metadata/license, cbor2 project metadata,
and the project’s approved `SCG-01` architecture decision.
