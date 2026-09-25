# Lucy-Nest source reconciliation

Date: 2026-09-25  
Base commit: `f21ccfdf9b80c5bbe25a9d138894bcbaace42387`  
Worktree: `task/lucynest-source-reconciliation-20260925`

## Purpose

Bring the currently active native Lucy-Nest implementation into the LucyOS
repository as reviewed, inactive source. This task does **not** replace the live
service, connect to the Nebula, change display ownership, install a boot hook,
or grant Lucy-Nest new authority.

## Source map

| Active source | Repo-owned destination | State |
|---|---|---|
| `lucy-nest-design-system/device/bridge.py` | `devices/little_lucy/bridge.py` | imported inactive; canonical AION APIs retained |
| `lucy-nest-design-system/device/client.py` | `devices/little_lucy/platforms/nebula/native/client.py` | imported inactive; flat Nebula deployment retained |
| `lucy-nest-design-system/device/ui.py` | `devices/little_lucy/platforms/nebula/native/ui.py` | imported inactive |
| `lucy-nest-design-system/device/font.ttf` | `devices/little_lucy/platforms/nebula/native/font.ttf` | DejaVu Sans; SHA-256 pinned |
| active `device/test_nest.py` | `devices/little_lucy/tests/test_native.py` and `test_native_bridge.py` | adapted to repo imports and isolated AION state |

No `connection.json`, token, private key, certificate, calibration file, log,
or other pairing/runtime state was copied.

## Architecture boundary

```text
Nebula 480x272 + touch
        |
        | paired TLS + bearer token
        | GET /status, POST /decision only
        v
Laptop bridge (inactive repo source)
        |
        | existing aion_core.tasks / approvals / security
        v
Canonical AION SQLite
```

The bridge projects redacted task and approval state. It does not create a
second task store, approval engine, queue, scheduler, or completion signal.
The native client renders locally; it is not a frame-streaming client.

## Authority status

The active external bridge can currently approve or deny a pending AION
approval after a paired-token, TLS, revision, and explicit-confirmation check.
That is a real owner decision surface, even though it is safer than an
unverified text alias.

This reconciliation therefore leaves authority unchanged and makes the issue
explicit. Before deployment, the owner must choose one of:

1. Lucy-Nest remains a secondary authenticated approval surface; or
2. Lucy-Nest is restricted to read-only status/display.

Until that decision, no repo source is wired into the live systemd unit.

## What is implemented here

- repo-owned bridge source with configurable bind host/port;
- canonical AION integration without a new state store;
- native client/UI source with package and flat-deployment import support;
- font asset and license provenance;
- isolated tests for calibration, confirmation, stale/offline behavior,
  approval replay, HTTP auth, route narrowing, and empty-state honesty.

## What remains gated

- physical Status → Het inbox touch calibration;
- real hardware approval and offline/reconnect evidence;
- stable LAN addressing and certificate rotation;
- systemd network-online/retry and sandbox hardening;
- native boot startup and reversible display restoration;
- the legacy port-18790 prototype, which must not run beside the native client;
- the authority choice above.

## Touch follow-up

A read-only 20-second capture on the running Nebula produced no input events.
The source parser has therefore been hardened to accept both common evdev
orderings and both legacy `ABS_X/ABS_Y` and `ABS_MT_POSITION_X/Y` codes. This
is source-only until the owner approves copying the updated client to the
device and restarting the native client.

The next physical check should be:

1. copy only the reviewed `client.py` source;
2. set `LUCY_NEST_RUNTIME=nebula` and
   `LUCY_NEST_DISPLAY_OWNER=confirmed` only in the native-client launch
   environment;
3. restart the existing native client without changing display ownership;
4. tap Home, then Status, then Het inbox;
5. inspect the client log and calibration result;
6. roll back the client copy if the touch path regresses.

No display takeover, firmware write, boot-hook change, or approval submission
is part of this check.

## Verification

Run from this worktree:

```sh
python3 -m unittest devices.little_lucy.tests.test_native_source -v
python3 -m unittest devices.little_lucy.tests.test_native -v
python3 -m unittest devices.little_lucy.tests.test_native_bridge -v
python3 -m unittest devices.little_lucy.tests.test_foundation -v
```

The full repository suite, secret scan, portability check, and live-untouched
check are recorded in `.unlazy/lucynest-source-reconciliation/GATES.md`.
