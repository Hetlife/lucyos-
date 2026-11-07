# PR102 security review — reproducible defects
Head reviewed: 387714c534e5945732e20f87e68a99e62f3161e6. Status: CHANGES REQUIRED; no merge approval.
Synthetic-only temporary AION_HOME; mocked clock and db.log_event. No production secrets/state read or written.
1. Existing same-name archive chmod 0644 remains 0644 after secrets_backup(). os.open(... O_CREAT|O_TRUNC, 0600) applies mode only to newly created files. Required result: enforce restrictive mode and atomically publish without permissive exposure.
2. Same-name archive symlink to a fixture outside BACKUPS/secrets is followed and its target overwritten. Required result: refuse/fail safely on symlink/collision; no unintended target mutation. Use reviewed exclusive/atomic file creation with cleanup and directory assumptions documented.
3. Timestamp has second granularity; concurrent calls/collisions and partial-write behavior need regression coverage before acceptance.
4. Configured AION_SECRETS outside private_state is excluded. Document/verify explicit coverage; do not falsely claim all secrets backed up.
5. Existing custom crypto is not independently cryptographically audited by this session. This review does not certify it.
Order: add failing fixtures -> scoped atomic-write correction in backup.py -> synthetic regressions -> full suite/security review -> owner merge -> separately authorized real escrow run/off-host copy and restore proof.
Executor: Claude Code when available; Codex fallback permitted if blocked. Scope backup.py and test_secrets_escrow.py. Do not touch real secret stores, authority, main or production services. Rollback: revert candidate commit; retain earlier archives. Escalate design/crypto uncertainty. FM-03 remains OPEN until corrected.
