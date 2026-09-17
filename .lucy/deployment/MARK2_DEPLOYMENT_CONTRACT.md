# MARK2_DEPLOYMENT_CONTRACT — for the Codex session with Mark-2 access

Authority: Fable, cycle 2026-09-16. Protected path (`.lucy/deployment/**`).
Executor: Codex with Mark-2 shell access. **You deploy an exact commit. You do not
design, refactor, or "fix while you're in there." If something in this contract
does not match the machine, stop and report; do not improvise.**

## 0. What you may deploy

| Candidate | SHA | Status |
|---|---|---|
| DC-0 substrate rehearsal | the `fable_freeze_sha` recorded in `.lucy/authority/HIGH_MODEL_BASELINE.json` on `integration/consolidation-20260916` | Rehearsal only: zero runtime behaviour change (adds CI, verifier, authority docs). Use it to prove the deploy procedure and `verify_authority.py deploy` on Mark-2. |
| DC-1 consolidation | `<<FABLE_NAMES_SHA>>` | **Not yet named.** Fable writes the literal SHA here after S-01..S-04 merge and FABLE-01 re-freezes. If this cell still reads `<<FABLE_NAMES_SHA>>`, DC-1 is not deployable. |

Never deploy a branch name. Never deploy a SHA that is not literally written in this file.

## 1. Pre-deploy snapshot (mandatory, before any file changes)

```
cd <lucyos checkout on Mark-2>
git rev-parse HEAD                       # record as PREVIOUS_SHA
./aion backup && ./aion backup --verify-only
./aion health > "$AION_HOME/BACKUPS/health-before-<SHA>.txt" ; true
systemctl --user list-timers --all | grep aion > "$AION_HOME/BACKUPS/timers-before-<SHA>.txt" ; true
```
Return PREVIOUS_SHA, the backup archive name, and the verify line in your evidence.

## 2. Fetch and verify the exact commit

```
git fetch origin
git checkout --detach <SHA>              # detached: a floating branch is never what runs
git rev-parse HEAD                       # must equal <SHA> exactly
python3 scripts/verify_authority.py deploy   # must print "ok": true
python3 -m unittest discover -s tests -t . -q
./aion scan .
```
If `deploy` mode reports drift or `fable_freeze_sha` PENDING: **stop**. That means the tree is not the frozen one.

## 3. Migrations

All migrations are additive (`CREATE TABLE IF NOT EXISTS`, `ALTER TABLE ADD COLUMN` via `db._migrate`). They run on first `./aion boot`. There is no destructive step and no manual SQL. After boot:

```
./aion boot
python3 - <<'PY'
from aion_core import db, skills
c = db.connect()
print("integrity:", c.execute("pragma integrity_check").fetchone()[0])
print("registry errors:", skills.validate_registry())   # must be [] on DC-1; may be non-empty on DC-0 (known DEGRADED, fixed by S-01)
PY
```

## 4. Service changes

DC-0: none. DC-1: none expected. The files under `systemd/` are templates:
`scripts/install_services.sh` substitutes `@REPO@` and `@AION_HOME@` before
writing them to `~/.config/systemd/user/`. Therefore **never compare raw
templates to installed units**. Verify the rendered forms instead:

```
python3 scripts/verify_installed_services.py
```

This command is read-only and must report `"ok": true`. If any unit is missing
or differs after rendering, report the exact unit and stop — unit changes are a
separate owner decision.

Also verify that an earlier owner pause has not left the autonomous timers
disabled:

```
systemctl --user is-enabled aion-work.timer aion-maintenance.timer
```

If either timer is disabled, report and stop unless the owner has explicitly
authorized resuming autonomous background work. Do not silently convert an
owner pause into a restart.

Restart the loop only after §2 and §3 pass, rendered units match, and the timers
are already enabled (or their re-enablement was separately owner-authorized):
```
systemctl --user daemon-reload
systemctl --user restart aion-work.timer aion-maintenance.timer
```

## 5. Secrets and owner actions

No secret values appear in this contract or in your report. Do not run `aion secrets` write operations. If `./aion health` reports `secret_store` missing, that is an owner action, not yours. Do not modify rclone remotes (owner action OWNER-04).

## 6. Health checks and double verification

```
python3 scripts/ci_health_gate.py                        # required checks
./aion health                                            # full picture; secret_store/backup lines are informational
./aion boot                                              # second fresh-process resume proof
./aion capabilities 2>/dev/null || true
```
Run the skill-registry line from §3 again. Watch one full timer cycle (`journalctl --user -u aion-work.service -n 50`) and confirm a session opened and closed.

## 7. Rollback

```
git checkout --detach <PREVIOUS_SHA>
systemctl --user daemon-reload && systemctl --user restart aion-work.timer aion-maintenance.timer
./aion boot && python3 scripts/ci_health_gate.py
```
The database needs no rollback: additive tables are ignored by older code. If integrity_check is not `ok`, restore the §1 backup with `./aion backup --verify-only` semantics (extract to a temp dir, then copy the DB file into `$AION_HOME`) and report.

## 8. Evidence to return (paste verbatim, redacted by `aion scan` if unsure)

1. PREVIOUS_SHA and deployed SHA (`git rev-parse HEAD` output).
2. `verify_authority.py deploy` JSON.
3. Unit-suite last three lines; `aion scan` last line.
4. §3 integrity + registry output.
5. §6 health-gate output and the journal excerpt showing one loop cycle.
6. `diff -r systemd/ …` result (empty or the diff).
7. Anything that did not match this contract, with the exact command and output.

## 9. Explicit prohibition

Do not invent architecture during deployment. Do not edit files. Do not "quickly fix" a failing test. Do not enable `resource_governor.enforce_admission`. Do not expose any port beyond loopback. If blocked, the correct output is a report, not a workaround.
