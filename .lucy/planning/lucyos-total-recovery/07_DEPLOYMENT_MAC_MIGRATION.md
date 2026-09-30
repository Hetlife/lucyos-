# 07 — Deployment now and Mac mini migration

## Roles now (canonical authority)
| Host | Role | Canonical? | Runs | Owns |
|---|---|---|---|---|
| **Lucy-den** (Ubuntu) | primary runtime + dev | **yes** — `<AION_HOME>` SQLite is the truth | `aion-work.timer` (10 min), `aion-maintenance.timer` (03:15), `aion-interface.service` (8787), OpenClaw, optional bridge | state, secrets, backups |
| **Mark-2** (DigitalOcean) | verification, rehearsal, overflow, restore drills | **never** | exact-SHA deploys per `.lucy/deployment/MARK2_DEPLOYMENT_CONTRACT.md`; `mark2-drive` sync | nothing canonical; its DB is disposable |
| **LucyNest** (Nebula pad + PWA) | owner status/approval surface | no | native client polling the laptop bridge; PWA via tunnel | nothing |
| **OpenClaw** (on Lucy-den) | channel + bounded executor | no | WhatsApp channel, `lucyosctl` calls | nothing; below LucyOS governance |
| **Drive** | transport for backups/handoffs | no | `LUCYOS_BACKUP`, `MARK2_SHARED` | nothing |
| **GitHub** | code truth + CI gates | yes for code | CI | code |

## State, backup, update, recovery (now)
- State: `<AION_HOME>` (default `~/openclaw/shared_brain`). Backups: `aion backup` nightly, restore-tested, optionally encrypted (`aion backup --encrypt`), secrets excluded. Export/import: `aion export` / `aion import`.
- Update promotion: PR -> CI green -> owner merge -> Lucy-den `git pull` (today) / `scripts/update.sh <sha>` (TR-6-04) -> `aion boot`, `aion verify` -> Mark-2 deploys the same SHA for double verification.
- Recovery: `aion boot` (never repeats the last action), `aion errors`, `aion health --deep`; restore = `aion import <archive>` then `aion boot`.
- Gaps: off-host backup not automated (ISSUE-021), update script absent (ISSUE-023), DC-1 SHA unnamed (ISSUE-022), live census absent (ISSUE-027).

## Mac mini migration (install / restore / promote, not redesign)
Preconditions (gates from `10_`): L1 green on main; L2 proven on Lucy-den; TR-2-02/2-03 backup+restore drill passed; TR-7-01 launchd loop fixed; TR-2-04 root-path defaults removed.

| Step | Command / action | Proof |
|---|---|---|
| 1 Freeze Lucy-den | `aion whatsapp pause`; `aion backup --encrypt`; `aion export ~/lucyos-export.tar` | archive verified (`backup --verify-only`) |
| 2 Copy | export archive + separately the 0600 `private_state/secrets.env` (never via Drive/chat; USB or scp over tailnet) | sha256 matches |
| 3 Mac bootstrap | Xcode CLT (`python3` >= 3.9), `git clone`, `scripts/install.sh`, `scripts/install_hooks.sh` | `aion health` healthy |
| 4 Restore | `aion import ~/lucyos-export.tar`; place `secrets.env` (0600); `aion boot` | task counts equal Lucy-den's; `aion verify` READY |
| 5 Services | `scripts/install_services.sh` (darwin branch) -> `launchctl bootstrap gui/$UID ...`; grant Login Items background permission | `launchctl list | grep com.lucyos` shows PIDs after reboot |
| 6 Local model | `brew install ollama` (or the app); `ollama pull llama3.1:8b` | `aion health` shows local models |
| 7 OpenClaw | install OpenClaw on the Mac; point its `lucyos` skill at the Mac's `AION_HOME`; WhatsApp channel re-linked | `aion openclaw-check` reachable; TR-1-05 E2E passes on the Mac |
| 8 Remote management | Tailscale (SSH + Serve for 8787); FileVault on; automatic login off, `sudo pmset -a autorestart 1 womp 1` | reboot test: services return within 3 min |
| 9 E2E | send `status`, `approve <ID>` from WhatsApp; nightly maintenance runs once | events + session rows on the Mac |
| 10 Promote | Mac becomes primary: Lucy-den `aion whatsapp pause`, its timers disabled; Mac `aion whatsapp resume` | `aion status` on both shows the role (meta `host_role`) |
| 11 Demote | Lucy-den = dev/secondary (worktrees, tests); Mark-2 = test/overflow/recovery | `host_role` values recorded |
| Rollback | Lucy-den still holds the pre-migration state; `aion whatsapp resume` there, disable Mac agents | — |

macOS specifics to design in, not bolt on: launchd (`RunAtLoad`, `KeepAlive`, `StartInterval`, `StartCalendarInterval`), no `loginctl linger` (Login Items instead), `/var` -> `/private/var` symlinks (already handled, M-01), Keychain optional later (secrets file stays), Gatekeeper/notarisation irrelevant for scripts, `caffeinate` not needed with `pmset`.

## Health, monitoring, security on the always-on host
- `aion health --deep` nightly (already); `aion supervisor` snapshot feeds LucyNest; `today` summarises activity.
- Loopback services only, exposed through Tailscale Serve/Funnel; token for PWA; HMAC + allowlist for the bridge.
- Secret store: one 0600 env file, backed up separately and encrypted; rotate by `aion secrets set`.
- Updates: `scripts/update.sh <sha>` with automatic rollback (TR-6-04); never `git pull` on the primary.
