# deploy/launchd/

Templates for `launchd` user agents on macOS, mirroring the four `aion-*`
systemd units. `@REPO@` and `@AION_HOME@` are substituted by
`scripts/install_services.sh` (darwin branch); do not load these files
directly.

| systemd source | plist | launchd key(s) |
|---|---|---|
| `aion-work.service` + `aion-work.timer` | `com.lucyos.aion-work.plist` | `RunAtLoad` |
| `aion-maintenance.service` + `aion-maintenance.timer` | `com.lucyos.aion-maintenance.plist` | `StartCalendarInterval` |
| `aion-bridge.service` | `com.lucyos.aion-bridge.plist` | `RunAtLoad` + `KeepAlive` |
| `aion-interface.service` | `com.lucyos.aion-interface.plist` | `RunAtLoad` + `KeepAlive` |

`mark2-*` units are Mark-2-host-specific (Desktop Commander, the Drive sync
cron) and are intentionally **not** mirrored here.

## Scheduling differences from systemd — documented, not invented

- **`aion-work`**: the systemd timer uses `OnBootSec=2min` (first run two
  minutes after boot) plus `OnUnitInactiveSec=10min` (re-run ten minutes
  after the previous run finishes). launchd has no single key that means
  "run once after boot, then again after the last run goes idle for N
  minutes" — `StartInterval` is wall-clock periodic regardless of whether
  the previous run is still active, which is a different guarantee, and
  `StartCalendarInterval` is calendar-based, not idle-based. Rather than
  approximate this with a key that means something subtly different, this
  plist only sets `RunAtLoad`: the build loop starts once when the agent
  loads (at login, or whenever `launchctl load`/`bootstrap` is run) and
  `scripts/build_loop.sh` is itself responsible for its own internal loop
  and exit conditions, exactly as it already is on Linux. If continuous
  re-launch after every exit is wanted later, that is a `KeepAlive` change,
  made deliberately, not folded into this translation.
- **`aion-maintenance`**: `OnCalendar=*-*-* 03:15:00` maps directly onto
  `StartCalendarInterval = {Hour: 3, Minute: 15}` — no gap here.
- **`RandomizedDelaySec=600`** (jitter) on the systemd timer has no launchd
  analogue and is dropped; the maintenance job runs at exactly 03:15 on
  macOS rather than with jitter. If the job's own idempotency already
  tolerates concurrent Linux+Mac schedules (it does — see
  `scripts/maintenance.sh`), this is a cosmetic difference, not a
  correctness one.
- **`Persistent=true`** (systemd: run immediately on next boot if a
  scheduled run was missed while the machine was off) has no launchd
  equivalent for `StartCalendarInterval`. A missed 03:15 run on a Mac that
  was asleep or off at that time is simply skipped until the next day.

## Hardening differences

The systemd units use `ProtectSystem=strict`, `ProtectHome=read-only`,
`NoNewPrivileges=true`, and `ReadWritePaths=@AION_HOME@` to bound what a bug
in the bridge or interface process can touch. launchd has no direct
equivalent to these Linux namespace/sandbox primitives; macOS's analogous
sandboxing (the App Sandbox / `sandbox-exec`) is a different, heavier
mechanism intended for signed, bundled applications, not a lightweight CLI
script, and is out of scope for this translation. This is a real reduction
in blast-radius containment on macOS relative to Linux — worth the owner
knowing, not worth pretending away.

## Installing

```
scripts/install_services.sh
```

writes each plist into `~/Library/LaunchAgents/` with `@REPO@`/`@AION_HOME@`
substituted, then loads it with `launchctl bootstrap gui/$(id -u)` (falling
back to `launchctl load` on older macOS where `bootstrap` isn't available).
Log directories under `@AION_HOME@/logs/` are created before load, since
launchd does not create `StandardOutPath`/`StandardErrorPath` parent
directories itself.

To stop an agent: `launchctl bootout gui/$(id -u)/com.lucyos.<name>` (or
`launchctl unload ~/Library/LaunchAgents/com.lucyos.<name>.plist` on older
macOS).
