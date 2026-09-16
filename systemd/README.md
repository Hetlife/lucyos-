# systemd/

Templates for `systemd --user` units. `@REPO@` and `@AION_HOME@` are substituted
by `scripts/install_services.sh`; do not run these files directly.

| Unit | Role |
|---|---|
| `aion-bridge.service` | Keeps the WhatsApp webhook bridge running, restarting on failure |
| `aion-maintenance.service` | One-shot nightly maintenance run |
| `aion-maintenance.timer` | Fires maintenance at 03:15 with jitter, catching up after downtime |

The bridge unit reads the token from the 0600 secret store at start rather than
holding it in the unit file, and runs with `ProtectSystem=strict` plus a single
writable path, so a bug in the bridge cannot write outside the shared brain.

User units stop when you log out unless lingering is on:
`loginctl enable-linger $USER`.
