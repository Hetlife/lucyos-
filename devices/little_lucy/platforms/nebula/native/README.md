# Nebula native Lucy-Nest source

This directory is the repo-owned source snapshot of the native client that is
currently deployed outside the repository at:

```text
/home/scs-admin01/lucy-nest-design-system/device/
```

It is **inactive source**. Importing it does not change the running laptop
bridge, the Nebula, display ownership, certificates, pairing material, or boot
configuration.

## Contents

- `client.py` — Nebula touch reader with order-tolerant evdev decoding,
  calibration, HTTPS-only TLS polling, explicit approval submission, and a
  root-only local Unix-socket remote-control channel (navigation; decisions
  gated off by default);
- `lucynest_ctl.py` — root-only local control client for the socket above;
- `ui.py` — local 480×272 Pillow renderer;
- `font.ttf` — DejaVu Sans rendering asset;
- `FONT-LICENSE.txt` — Debian font license/provenance;
- `__init__.py` — package marker for repository tests.

The deployable Nebula layout remains flat: `client.py`, `ui.py`, and `font.ttf`
are copied together to `/root/lucy-nest/native/`. The package import fallback
in `client.py` exists only so the same source can be tested from LucyOS.

## Import provenance

- Imported: 2026-09-25
- Source workspace: `/home/scs-admin01/lucy-nest-design-system/device/`
- `font.ttf` SHA-256:
  `ae7b7855e115a5966d8b1b3f80f254ccc117ec86f9965e202ee2940453837280`
- Font identification: DejaVu Sans
- No `connection.json`, token, private key, certificate, log, or calibration
  state was imported.

## Root-only remote control (local Unix socket)

`client.py` optionally serves a **local-only** remote-control channel so root on
the Nebula itself can inspect and navigate the on-screen UI over an existing
SSH session. It never opens a network listener: the socket is `AF_UNIX`
(`SOCK_STREAM`) only.

- Socket: `/run/lucy-nest/control.sock`; the directory `/run/lucy-nest` is
  created as a real directory with mode `0700` (symlinks or non-directories are
  refused), the socket is bound with umask `077` and forced to mode `0600`.
- Every connection must present `SO_PEERCRED` uid `0`; anything else — including
  a kernel without `SO_PEERCRED` — is refused. One request per connection, 2 s
  timeout, one JSON line reply (`{"ok": true, ...}` / `{"ok": false, ...}`).
- Requests are a single UTF-8 line, at most 256 bytes: `VERB` or `VERB ARG`.
- Replies never contain tokens, URLs, or other secrets — only the small status
  snapshot (page, index, pending count, focused id/title truncated to 80
  characters, online flag, last update time, touch status).

### Verbs

| Verb | Class | Effect |
|---|---|---|
| `status` | read-only | JSON snapshot of the current screen (see above) |
| `home` | nav | back to the eyes/home page |
| `inbox` | nav | open the pending-approvals inbox |
| `next` | nav | highlight the next pending approval |
| `review` | nav | open the currently highlighted approval |
| `detail_next` | nav | next detail page while reviewing |
| `review_back` | nav | previous detail page / back to the inbox |

Navigation verbs only drive the existing `apply_action()` flow; they never
stage a decision and never submit anything.

### Decisions are disabled by default

`approve`, `deny`, and `send` exist as verbs but are refused unless **all** of
the following hold:

1. `/root/lucy-nest/native/remote-decisions.enabled` exists as a regular,
   non-symlink, root-owned (`uid 0`) file with mode `0600` whose first line is
   exactly `ALLOW_REMOTE_DECISIONS` (the client never creates this file);
2. the shown selection still matches the currently pending approval
   (approval id **and** revision);
3. the request then flows through the exact existing touch path
   (`apply_action()` → the single `/decision` submission). No new fields are
   added and no second approval engine exists.

Enabling remote decisions (on-device, as root):

```sh
mkdir -p /root/lucy-nest/native
printf 'ALLOW_REMOTE_DECISIONS\n' > /root/lucy-nest/native/remote-decisions.enabled
chown root:root /root/lucy-nest/native/remote-decisions.enabled
chmod 0600 /root/lucy-nest/native/remote-decisions.enabled
```

### Usage

On the Nebula (as root, e.g. over SSH):

```sh
python3 lucynest_ctl.py status
python3 lucynest_ctl.py inbox
python3 lucynest_ctl.py send A-1   # only when the gate is enabled
```

Exit codes: `0` ok, `1` refused (not root, bad verb, or server refusal),
`2` unreachable.

### Rollback

Remote control is inert if the control server never starts. To disable it,
remove the socket directory and reload the client without the control thread
(or revert this change):

```sh
rm -f /run/lucy-nest/control.sock && rmdir /run/lucy-nest
rm -f /root/lucy-nest/native/remote-decisions.enabled   # keep decisions off
```

Deleting the gate file immediately re-disables remote decisions even if the
socket remains up.

## Safety boundary

The client is allowed to:

- read Nebula touch input locally;
- render locally;
- request sanitized status;
- submit an explicit, fresh approval decision over the paired TLS bridge.

It is not allowed to:

- create tasks or approvals;
- call arbitrary commands;
- access camera frames or secrets;
- claim task completion;
- take permanent display ownership;
- install itself at boot.

Physical display takeover, boot startup, and the legacy port-18790 client remain
separate gated work.
