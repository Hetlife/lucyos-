# Operations

## Install on the Ubuntu PC

```bash
git clone <this repo> ~/lucyos
cd ~/lucyos
scripts/install.sh          # symlinks `aion`, creates the brain, first backup, health
scripts/install_hooks.sh    # pre-commit: secret scan + tests
aion owner-setup            # the batched list of what you still need to provide
```

Nothing above needs a credential. `install.sh` is idempotent.

## Run it continuously

```bash
aion secrets set WHATSAPP_BRIDGE_TOKEN   # value entered here, never in chat
scripts/install_services.sh
systemctl --user enable --now aion-bridge.service
loginctl enable-linger "$USER"           # keep running when logged out
```

The nightly timer runs `scripts/maintenance.sh` at 03:15: boot loop, notebook
sync, backup with a real restore test, doc regeneration, secret scan and a deep
health check, all inside one logged session.

## Daily use

The owner uses WhatsApp. On the machine:

```bash
aion boot        # startup and resume: never blindly repeats the last action
aion report      # the full picture
aion tasks       # ranked by expected value
aion blockers    # only what needs a human
aion why <ID>    # explain any decision, approval, task or error
```

## Secrets

```bash
aion secrets init         # creates private_state/secrets.env at 0600
aion secrets set NAME     # prompts hidden; the value is never logged or stored in the database
aion secrets list         # names only, never values
```

Secrets are excluded from backups on purpose, so an archive copied to a shared
drive carries no credentials. Back up `private_state/` separately and encrypted.

## Backup and restore

```bash
aion backup                 # create, then immediately restore-test it
aion backup --verify-only   # re-verify the latest archive
```

`verify` extracts to a temp directory and opens the database, so a backup is
only reported healthy after it has actually been restored. The last 14 are kept.

To restore for real: stop the bridge, extract the archive over the shared brain,
run `aion health --deep`.

## Recovery after a crash or a model switch

Run `aion boot`. It verifies the brain, ingests the sync inbox, applies notebook
entries, releases stale task claims, checks approvals and failures, runs health
and names the current bottleneck. It reports the previously recorded next action
rather than re-running it, so an interrupted external action is not duplicated.

## Talking to other AI sessions

Another session emits an AI SYNC PACKET (format in
`directives/05_SYNC_AND_HANDOFF_PROMPT.txt`). Drop the file into
`INBOX/pending/` and run `aion ingest-inbox`, or `aion ingest <file>`. Packets
are deduplicated by content, so re-sending the same work under a new id is safe,
and a fact that contradicts local memory is flagged rather than overwritten.

## Cost control

```bash
aion route <kind> --complexity 3 --stakes high   # which class should do this
aion usage <model> <class> --cost <INR>          # record spend
aion money                                       # governor state and real money
```

The governor moves NORMAL → ARCHITECTURE-DONE → SHIFT-DOWN → RESERVE →
CRITICAL-ONLY → HANDOFF → STOP as the strong-model budget is consumed.

## When something breaks

```bash
aion errors                                   # unresolved failures
aion error-add <component> "<message>"        # record one
aion error-resolve <ID> --root-cause "..." --fix "..." --lesson "..."
```

The lesson goes into searchable memory, so the same failure is not rediscovered.
Anyone — you, ChatGPT, Claude, OpenClaw — can also just append a `[BUG]` entry to
`NOTEBOOK.md`; the next sync turns it into a task and an error row.
