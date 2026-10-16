# Context packet v1
Source: existing AION tasks, repository HEAD and explicitly selected file ranges. API: context.compile_agent_packet(task_id, role, slices, budget_bytes, expected_sha).
Stable cacheable prefix is emitted first and includes durable security constraints. Dynamic last: canonical task metadata, SHA, project, acceptance, selected (path,start,end,sha256,content), and verifier boundary. SHA mismatch fails; context is not silently reused.
Caps: 2-16 KiB total; <=6 file slices; <=80 lines/slice; each source <=128 KiB; no directory expansion, hidden paths, symlinks or upward traversal. Sensitive-looking content fails closed. Context budget overflow fails instead of trimming policy/acceptance.
CLI: ./aion context TASK-ID --harness-role cheap --slice tests/base.py:1:6 --budget-bytes 8192 --expected-sha SHA
A low-cost agent only gets this packet; expansions need an explicitly amended scope/revision, not an unrestricted repository dump. Existing ./aion context remains unchanged unless --harness-role is specified.
Tests include size, stale SHA, unsafe slices, source hash and untrimmed acceptance.

Before real execution, `context.agent_packet_is_fresh(packet)` must re-hash the serialized packet, compare the source Git HEAD AND each included source file's current SHA-256. This catches dirty/uncommitted changes as well as a changed commit and altered task metadata. The adapter still needs canonical AION task claim and scope checks; this predicate by itself grants no authority. `tests/test_agent_packet_freshness.py` covers tampering, changing HEAD and changing file content hashes.
