# Mark-2 Google Drive exchange

The bridge exchanges staged, scanned documents through `gdrive:MARK2_SHARED`.
GitHub remains authoritative for code. The local AION SQLite database and shared
brain remain authoritative for operations. No canonical loop files are modified.
No paid APIs, model calls, mounts, automatic deletes, or general directory syncs
are used. ChatGPT's own account connection is separate and cannot be verified by
this server; select the same dedicated Google account during authorization.

## Commands

```sh
mark2-drive status
mark2-drive stage --kind handoffs --file /path/to/reviewed-handoff.md
mark2-drive stage --kind reports --file /path/to/reviewed-report.json
mark2-drive push-handoffs
mark2-drive push-reports
mark2-drive push-context
mark2-drive pull-inbox
mark2-drive test
mark2-drive sync
```

`status` generates a compact export locally. `stage` is the explicit publication
boundary: use it only on a reviewed, non-secret document. Exports are limited to
UTF-8 Markdown, text and JSON, 256 KiB per file. Raw shared-brain documents, logs,
backups, database files and repositories are never automatically copied.
AION's scanner plus stricter path, JSON sensitive-field, OAuth-pattern, binary,
size, symlink/hardlink and opaque-content checks reject suspect input before
upload. Staged content is scanned again and uploaded from a private snapshot.
Detection is defense in depth, not proof that arbitrary prose contains no secret;
review at staging remains necessary. Rejected content is not automatically
redacted and shipped. Structured status contains only fixed labels, counts,
validated local IDs and timestamps, not task descriptions or private messages.

Reports/handoffs use immutable content-addressed names. Only the generated
`03_CONTEXT/MARK2_STATUS.json` is intentionally replaced. Successful uploads are
read back and SHA-256 verified before committing the local ledger. Unchanged
staged documents are skipped. Missing/replaced remote objects are not discovered
by the local skip optimization; use the safe test and an explicit republish if an
owner edits or deletes exported objects on Drive. Do not edit server exports on
Drive; put new material in the inbox instead.

## Inbox contract and trust

Place plain UTF-8 `.md` or `.txt` AI SYNC PACKET documents in `00_INBOX`:

```text
# AI SYNC PACKET
SOURCE: ChatGPT
PROJECT: default
## TASKS CREATED
- Review the Drive exchange | 3 | none | Verify owner-readable status
END AI SYNC PACKET
```

Allowed sections: TASKS CREATED, RESEARCH FINDINGS, RISKS, APPROVALS REQUIRED.
They are external requests/claims, not executable instructions or approved actions.
Existing AION parsing creates tasks in TRIAGE; only the existing approval system
can grant approvals. Canonical resume overrides and asserted VERIFIED FACTS are
rejected. Google-native Docs need export as a plain file first.

Delivery uses existing `INBOX/pending`, with immutable path-plus-content names.
The canonical ingestion process, when run, moves files to `processed`/`failed`;
the Drive bridge observes those locations and records the result. It does not
run the whole canonical loop or ingest unrelated local files. If the existing
loop is stopped, files remain queued. Drive sources are always retained.
Malformed or secret-bearing files stay on Drive; only hashed identities, fixed
error codes and timestamps are recorded locally. Correct the Drive file to retry.
Ordinary text without packet headers is rejected, not converted into a task.
The owner-specified first live check is `00_INBOX/mark2-drive-test.txt`.

## Local state and recovery

- Code: `bridges/drive_bridge.py`; CLI: `scripts/mark2-drive`.
- Staging: `OUTBOX/drive/{handoffs,reports,context}` under AION_HOME.
- Ledger/lock/auth gate: `state/drive_bridge` under AION_HOME, private directory.
- Credential store: `/root/.config/rclone/rclone.conf`, mode 0600, directory 0700.
- Status: `OUTBOX/drive/context/MARK2_STATUS.json`.

Every completed transfer is checkpointed with atomic replace/fsync. Delivery
intent is saved before publishing a complete inbox file using no-replace linking.
A crash before ledger commit safely reconciles the same immutable local filename.
Conflicts and missing deliveries fail explicitly. Failed network operations keep
staged data and prior ledger entries. Retry by rerunning the same command.
The ledger is local-only and is not the operational database.
Rclone gets three attempts, 1s/2s backoff, and a 45-second per-attempt deadline.
No remote error text or private filenames are printed. Directory listing is
limited to 1,000 entries and 4 MiB returned output; the service also has a total
240-second bound. A single process-wide file lock prevents overlap.

## Authorization and activation

Rclone is already installed; no extra package installation is needed.
Current rclone warns its shared Google OAuth client is retiring. Use a Google
Desktop OAuth client owned by the dedicated Mark-2 account/project:

1. In https://console.cloud.google.com/apis/library/drive.googleapis.com enable
   Google Drive API in the dedicated account's project.
2. In https://console.cloud.google.com/auth/clients configure consent/audience
   as necessary and create a Desktop app OAuth client. For lasting unattended
   access, use an appropriate production/internal consent configuration; external
   testing grants can expire. Keep access limited to the dedicated account.
3. Supply its JSON locally as `/root/.config/rclone/google-oauth-client.json`
   with mode 0600, using a secure local file transfer. Never send it through chat,
   Drive or Git. This is the owner credential-provisioning step.
4. The operator runs `scripts/authorize_drive.py --client-file` with that path,
   with a private browser route/SSH tunnel to localhost:53682 ready. The helper
   emits only the temporary local login URL and times out after ten minutes.
   The owner signs in using the dedicated account and approves Drive access.
   The client material and refreshed authorization remain in protected rclone
   config. The input JSON can be removed locally after successful import.
5. The operator runs `mark2-drive test` (creates the nine folder paths and retains
   one harmless archive test file), verifies the requested inbox test, and runs
   `scripts/install_drive_bridge.sh --enable`. This performs another real test and
   full manual sync before enabling the timer. No owner terminal work is needed
   for these operator-run commands.

Folders: `00_INBOX`, `01_LUCYOS`, `02_STRATEGY_FACTORY`, `03_CONTEXT`, `04_REPORTS`,
`05_HANDOFFS`, `06_APPROVALS`, `99_ARCHIVE`, all below `MARK2_SHARED`.

## Separate automation

`systemd/mark2-drive.service` and `.timer` are standalone. The installer without
`--enable` installs units and the command only; it does not start synchronization.
The service requires the successful live-test gate. Timer cadence is five minutes
after the previous run, with jitter. Runs have a 240-second limit, 256 MiB memory
limit, restricted write paths, private temporary directory and no new privileges.
No restart loop is configured. User linger is already enabled on Mark-2.

```sh
systemctl --user status mark2-drive.timer mark2-drive.service
journalctl --user -u mark2-drive.service -n 20 --no-pager
systemctl --user disable --now mark2-drive.timer
```

Revoking the Google OAuth grant and stopping the timer reverses authorization and
automation. Existing local and remote documents are retained.

## Validation and deployment checkpoint

Offline tests: `python3 -m unittest tests.test_drive_bridge -q`.
Regression/security tests: `python3 -m unittest discover -s tests -t . -q`,
`./aion scan .`, `git diff --check`.
Actual authorization, remote read/write, live round-trip and scheduled sync
remain pending until OAuth is completed. A fake-remote test is not evidence of a
live Drive connection. Unit syntax and the unauthenticated service gate can be
checked before OAuth without enabling the timer.

References: https://rclone.org/drive/#making-your-own-client-id and
https://rclone.org/remote_setup/#configuring-using-ssh-tunnel
