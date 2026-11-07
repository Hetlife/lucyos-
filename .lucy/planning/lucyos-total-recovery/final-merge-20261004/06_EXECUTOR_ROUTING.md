# Low-token execution
DETERMINISTIC first: branch ancestry/patch IDs, file hashes, checks, tests, packet construction.
OpenClaw: existing bounded health/reporting and owner-message route, no architecture, no new approvals system.
Claude Code on Lucy-den: one named work order in a separate worktree; exact allowlist and acceptance commands.
Codex: runtime ownership, Lucy-den/Mark-2/pad, GitHub/Drive, deployment and integration. Framer stays off-path unless needed.
High-capability: security review, ambiguous root cause, DAG/authority and batch verification.

No active autonomous job was launched by this audit. No claim that another executor is working.
Minimum packet: baseline (<~2k tokens target) + one order + exact file slices + relevant tests + known root-cause IDs. Target task packet <=6k tokens; exceed only with an explicit reason. Never send all 55 orders or the whole repo.
Store file hashes + base SHA. Reuse results until a relevant file, service target, schema or policy changes. Two materially identical failed attempts => escalate with commands/errors/diff, not another whole-repo read.
Use existing task claim/lease mechanisms; path locks below are planning conflicts, not a replacement runtime lock manager.
Local inference is not enabled merely because Ollama exists: Lucy-den has an active no-local-models timer. Resolve that policy first.
