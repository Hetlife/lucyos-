# First dependency-correct batch

| ID | Priority | Executor | Dependencies | Lock |
|---|---|---|---|---|
| FM-01 | P0 risk | CODEX | none | runtime-control-plane |
| FM-02 | P1 | CLAUDE_CODE on Lucy-den | none | scripts/build_loop.sh |
| FM-03 | P1 | HIGH_CAPABILITY security review then CLAUDE_CODE | none | aion_core/backup.py; aion_core/cli.py |
| FM-04 | P1 | CLAUDE_CODE on Lucy-den | none | scripts/verify_installed_services.py |
| FM-05 | P1 | CODEX | none | lucynest-runtime |
| FM-06 | P2 | CODEX + deterministic Git | none | merge-ledger |
| FM-07 | P1 | OPENCLAW + CODEX; owner phone for origin proof | FM-01 | canonical-approvals |

Planning identifiers only. Reuse/bind canonical task/session before execution; this audit did not create parallel task infrastructure.


FM-09: camera retry repair, held on verified source provenance; depends on FM-05.
