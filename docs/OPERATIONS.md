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
aion secrets set WHATSAPP_ACCESS_TOKEN   # values entered here, never in chat
aion secrets set WHATSAPP_PHONE_NUMBER_ID
aion secrets set WHATSAPP_VERIFY_TOKEN
aion secrets set WHATSAPP_APP_SECRET
aion secrets set WHATSAPP_GRAPH_API_VERSION
aion secrets set WHATSAPP_ALLOWED_SENDER   # owner phone in international digits only
scripts/install_services.sh
systemctl --user enable --now aion-bridge.service
loginctl enable-linger "$USER"           # keep running when logged out
```

## Private phone interface

Set a separate interface token locally, install the service, and keep it bound
to loopback:

```bash
aion secrets set AION_INTERFACE_TOKEN
scripts/install_services.sh
systemctl --user enable --now aion-interface.service
systemctl --user status aion-interface.service
```

From a laptop, an SSH tunnel is enough: `ssh -N -L
8787:127.0.0.1:8787 <ubuntu-pc>`, then open `http://127.0.0.1:8787`. For an
iPhone and home-screen installation, expose the same loopback service through
a private HTTPS tunnel such as Tailscale Serve. Never bind port 8787 to a public
interface. Enter the token once in the page; **Forget this device** removes it.
The page caches only its summary snapshot and queues captures while offline;
the full report is never persisted in browser storage.

The nightly timer runs `scripts/maintenance.sh` at 03:15: boot loop, notebook
sync, backup with a real restore test, doc regeneration, secret scan and a deep
health check, all inside one logged session.

## WhatsApp Cloud API bridge (public callback)

`aion-bridge.service` runs the Meta Cloud API adapter on `127.0.0.1:8765`.
Meta delivers messages by POSTing to a public HTTPS URL, so unlike the private
phone interface above, **this endpoint must be reachable from the public
internet.** A tailnet-only URL (Tailscale Serve) cannot receive Meta's calls; a
public tunnel can. The bridge itself stays on loopback: never bind it to
`0.0.0.0`, and expose it only through a TLS-terminating tunnel or reverse proxy
that forwards to `127.0.0.1:8765`.

What protects a public endpoint is already in `bridges/whatsapp_bridge.py`:

- **Handshake (GET)**: `hub.mode=subscribe` and a `hub.verify_token` that matches
  `WHATSAPP_VERIFY_TOKEN` (constant-time compare), otherwise 403.
- **Messages (POST)**: `X-Hub-Signature-256` must equal
  `sha256=HMAC-SHA256(WHATSAPP_APP_SECRET, raw body)`, otherwise 401 and a
  `whatsapp.signature_failed` event. Bodies over 64 KiB get 413.
- **Sender allowlist**: only `WHATSAPP_ALLOWED_SENDER` is answered; anyone else
  is dropped and logged as `whatsapp.sender_rejected`.

Known limits to accept before exposing it: the server is single-threaded with no
per-connection timeout and no rate limiting, so one stalled or abusive
connection can block it; the HTTP access log is suppressed; and behind a tunnel
every request arrives from `127.0.0.1`, so an event's subject cannot tell you
who sent it. None of this exposes data, but it can make the bridge unavailable.

### Steps

1. **Set the six values** (`aion owner-setup` lists where to find each), each with
   `aion secrets set <NAME>`. The service refuses to start without all of them.
2. **Install and start the service** with `scripts/install_services.sh`, which
   prints the start command for your platform. It restarts every 5 seconds if it
   exits, so a missing variable shows up as a crash loop, not one clear error.
3. **Run the preflight before touching Meta:**

   ```bash
   python3 scripts/bridge_preflight.py
   ```

   It checks, without printing any value, that the six variables are set, that
   the port is listening, and that a wrong verify token gets 403. Add
   `--probe-signature` to also confirm an unsigned POST gets 401; that writes one
   `whatsapp.signature_failed` event, which is indistinguishable from a real one
   once tunnelled, so expect exactly one in step 6 if you use it.
4. **Expose the port.** Use any HTTPS tunnel or reverse proxy that forwards to
   `127.0.0.1:8765`. Tailscale Funnel, Cloudflare Tunnel or your own proxy all
   work; some cost money or need an account, so that choice is yours and nothing
   here creates one. You need a stable `https://` URL whose root reaches the
   bridge.
5. **Configure Meta.** In the app's WhatsApp webhook settings, set the callback
   URL to that `https://` URL and the verify token to the exact value you stored
   as `WHATSAPP_VERIFY_TOKEN`, then subscribe to `messages`. Meta sends the GET
   handshake immediately; the console shows it as verified only if the bridge
   echoed the challenge.
6. **Send a real message** from the allowed number, for example `status`. Expect
   a reply within seconds. Then run `aion today`: the activity line should show
   your traffic and no unexpected `whatsapp.signature_failed` or
   `whatsapp.sender_rejected`.

If the handshake fails, re-run the preflight first; it tells you whether the
problem is local (variables, port) or between Meta and the tunnel.

### What this does not prove

The preflight proves the bridge starts and its two gates are live on loopback.
It does not prove Meta can reach your URL or that a message reaches a phone;
only step 5 and step 6 with your real credentials do that.

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

### Encryption (optional)

```bash
aion secrets set BACKUP_PASSPHRASE   # prompts hidden; never logged or stored in the database
aion backup                          # now encrypted; verify still round-trips
```

With no `BACKUP_PASSPHRASE` configured, backups are unencrypted exactly as
before, and the archive's log line says so explicitly (`aion status` /
`events` shows `unencrypted (no BACKUP_PASSPHRASE configured)`), never
silently.

This is not AES: LucyOS carries no third-party dependency, so the
implementation is an HMAC-SHA256 keystream for encryption plus a separate
HMAC-SHA256 tag over the salt, nonce and ciphertext for authentication
(encrypt-then-MAC), built entirely from the standard library's `hmac` and
`hashlib`. A wrong passphrase or a tampered archive fails the MAC check and
`aion backup --verify-only` reports it as a clean failure — never a corrupt
"success". Treat this as adequate for an off-host copy of an already
locally-verified backup, not as a substitute for a real audited cipher if
the threat model ever requires one.

**Never** put the passphrase in a commit, a log line, a chat message, or an
approval/task description — `aion secrets set` is the only place it is
typed, and it never enters the database.

### Off-host copy drill (manual — nothing here is automated tonight)

The backup archive under `$AION_HOME/BACKUPS/` is local. A lost or corrupted
machine loses every backup with it unless a copy exists somewhere else. This
repo intentionally does not automate an upload (that needs credentials this
task is forbidden from requesting or storing), so run this by hand
periodically, or wire it into your own off-host tooling once the Mac
migration (S-23's `aion export`) is in place:

1. `aion secrets set BACKUP_PASSPHRASE` once, if you want the copy encrypted
   at rest on the destination (recommended for anything leaving this
   machine).
2. `aion backup` — creates and restore-verifies the latest archive.
3. Copy the newest file in `$AION_HOME/BACKUPS/aion-backup-*.tar.gz` to a
   second location you control: a USB drive, a second machine over `scp`, or
   a personal cloud drive you already trust with other backups. The archive
   itself never contains `private_state/` or any secret, encrypted or not —
   only the passphrase, entered separately at restore time, protects its
   *contents* if the destination is not fully trusted.
4. On the destination, confirm the copy is intact: `sha256sum` it and
   compare against the source before deleting anything.
5. To restore from an off-host copy: bring the archive back onto the
   machine, run `aion backup --verify-only` against it (or point
   `aion_core.backup.verify(path)` at it directly), then extract over the
   shared brain as in "Backup and restore" above.

There is no scheduled/automatic off-host copy in this repository as of this
task — that is intentionally an owner decision (what destination, what
credentials, what cadence), not something to wire up silently.

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
