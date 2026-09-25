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
  calibration, HTTPS-only TLS polling, and explicit approval submission;
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
