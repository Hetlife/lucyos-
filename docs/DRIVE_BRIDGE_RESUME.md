# Mark-2 restart checkpoint — 2026-09-08

## Current owner instruction

Save everything at a clean recovery point so work can resume after the Codex
usage limit resets. Do not restart or change the canonical operating loop.
A limit reset does not itself launch Codex. The next authorized session/run must
read this file; no new paid-usage scheduler has been installed.

## Delivered and verified

- `/root/lucyos`, branch main, remote `Hetlife/lucyos-`.
- Implementation commits: `d17c9cd` and `9e22748`.
- Installed rclone 1.75.1 and Ollama 0.33.3 reused; no duplicate infrastructure.
- `mark2-drive status`, `pull-inbox`, `push-status`, `push-reports`,
  `push-handoffs`, `test`, `sync`, and explicit `stage` implemented.
- 159 regression tests passed, including 19 bridge safety/recovery tests.
- Secret scan and Git whitespace checks passed.
- Separate Drive service/timer installed, syntax verified; authorization gate
  verified; timer deliberately disabled pending real manual Drive success.
- Shared-brain SQLite, canonical loop, approval and execution logic unchanged.
- Local status export exists at
  `/root/openclaw/shared_brain/OUTBOX/drive/context/MARK2_STATUS.json`.
- Local bridge ledger/recovery state is under
  `/root/openclaw/shared_brain/state/drive_bridge/`.
- Pre-change Git bundle: `/root/drive-setup/pre-bridge.bundle`.
- Pre-change AION backup: `aion-backup-20260908T145104+0000.tar.gz`, restored with
  database integrity OK (13 tasks, 18 memories). Backups remain local.

## Actual blocker (updated 2026-09-09)

The protected `gdrive` remote now references the locally supplied service-account
file and enables Shared-with-me visibility. Credential structure and identity
were validated without displaying secret fields. Google rejected the first live
listing because the Google Drive API is disabled in the credential's Cloud
project. The project owner must enable that API; browser OAuth is no longer part
of this integration.

## Exact next actions for the resuming agent

1. Read this file and `docs/DRIVE_BRIDGE.md`; verify Git state and inspect
   credential presence only, never print credential values. Reuse existing setup.
2. Confirm the project owner has enabled Google Drive API, then verify
   `rclone lsd gdrive:` and
   `rclone lsd gdrive:MARK2_SHARED` without printing arbitrary private filenames
   or raw errors into chat. Record successful read access honestly.
3. Verify `MARK2_SHARED/00_INBOX/mark2-drive-test.txt` supplied by the user.
   Scan locally before displaying anything. Ordinary text is not a task packet;
   if it lacks the documented packet format, report the rejection and retain it.
4. Run `mark2-drive test`. This creates/reuses folders and verifies a harmless
   unique write/list/read/delete round-trip. Do not fabricate a passed
   live test from the offline fake-remote tests.
5. Run `scripts/install_drive_bridge.sh --enable`: it requires a successful live
   test and manual sync before enabling the independent timer, then publishes
   the exact readiness handoff and status paths. Verify real timer execution and
   remote files `05_HANDOFFS/MARK2_BRIDGE_READY.md` and
   `03_CONTEXT/MARK2_STATUS.json` afterward. Recover any failures from the ledger.
6. Update notes/checkpoint and commit relevant changes after appropriate checks.
   Report only the seven fields requested by the owner: Drive connected, bridge
   location, automatic sync, tests, Git commit, remaining blocker, exact owner
   action if any. Then continue independent authorized work.

## Boundaries and independent follow-up

Keep GitHub canonical for code and local shared-brain state canonical for
operations. Drive is a document transport only. Security decisions use
strict deterministic checks, not the small model. No raw logs, credentials,
private_state, database, browser data or unreviewed directories are exported.
No Drive packet can grant approvals or replace the canonical resume point.

The existing maintenance service exited 1 and the existing work timer was
active/elapsed without a scheduled next run. Six open errors were categorized
as command failures without printing raw private logs. Paused and safe_mode
flags were false when checked. Do not silently clear errors or restart/modify
the loop. Diagnose read-only; any actual loop change needs LOOP_CHANGE_REQUEST.

Ollama is running with `qwen2.5-coder:0.5b` as the local-ai CLI default and 1.5B
available. The AION worker's default model configuration has NOT been changed;
changing execution routing needs its applicable review, not an implicit reset.
