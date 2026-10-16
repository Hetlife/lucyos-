# Checkpoint / restart safety
2026-10-16: separate isolated worktree on Lucy-den; base GitHub main e349bb03446452bace3a5225d990a73bae8160e1. Existing dirty Lucy-den and Mark-2 worktrees untouched.
Recovery command: locate worktree via git -C /home/scs-admin01/lucyos worktree list; read branch and current SHA; read EVIDENCE_INDEX.md; rerun focused tests and required gates; inspect canonical SQLite before attaching task; do not trust status markdown over DB.
The existing aion_core/resume.py and tasks.py own durable progress; do not create new checkpoint/queue. No primary migration, service restart or SQLite restore was undertaken. Mark-2 remains secondary. Never report queued WhatsApp as delivered.

Verified W1/W2 bootstrap commit 9292e761; W2b multi-agent collaboration/dispute commit 26d6d826 on isolated non-protected branch. Both real AION-home runtime DBs unchanged by checkout work. Local isolated pilot AION_HOME=/tmp/lucy-harness-pilot-20261016 created only disposable state; no production AION task modified. Preserve existing dirty host worktrees.
