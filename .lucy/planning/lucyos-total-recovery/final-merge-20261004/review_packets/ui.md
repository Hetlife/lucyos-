# LucyNest/UI/API
Status: PREPARED, review NOT claimed complete.
Executor: deterministic inventory first, then bounded Claude Code review; high model only for security/ambiguity.
Base: e349bb03446452bace3a5225d990a73bae8160e1.
Read baseline then only: bridges/http_server.py, aion_core/api.py, web/.
Relevant tests: tests/test_http_interface.py. Confirm paths exist; a missing name is a packet defect, not permission for a whole-repo scan. For directories select the exact relevant files in the manifest before dispatch.
Known focus: FM-B05/06; branch native source only after exact snapshot.
Checklist: state transitions; race/idempotency; stale assumptions; error handling; duplicated state; security boundaries; input validation; contract mismatches; missing tests; machine paths; dead code/complexity.
Return reproducible evidence and root-cause IDs, or NO FINDING with reviewed files/hashes. Do not fabricate a bug from a name.
No code changes in review. Any fix needs its own exact allowlist/test/rollback order. Two matching failed attempts escalate. Model packet ceiling 6k tokens; split by function before exceeding.
