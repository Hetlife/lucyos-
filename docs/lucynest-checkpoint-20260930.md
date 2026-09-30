# Lucy-Nest checkpoint — 2026-09-30

## Summary

Phase 1 software work is complete and verified (99 tests). On-device work
established two things that correct the previous checkpoint:

1. **Touch hardware works.** The earlier "NS2009 senses no pressure, taps
   generate no IRQ" conclusion was wrong.
2. **The display is not showing the native UI.** The panel is frozen on the
   Creality boot logo because the LCD/layer-mixer is not driving it. This was
   misdiagnosed earlier as an overlay/logo-layer problem.

## Software: Phase 1 complete

All under `devices/little_lucy/platforms/nebula/native/`:

- `action_schema.py` — bounded action batches, stable SHA-256 digest.
- `authorization.py` — approval bound to batch digest + revision + request id,
  expiring, one-use, persisted.
- `hid.py` — HID keyboard/mouse reports, mock transport, release-all.
- `capture.py` — PC capture metadata and native→PC coordinate mapping.
- `client.py` / `ui.py` — review/confirm/executing/result/STOP surfaces and an
  injected executor that refuses without a passing authorization.
- `screenshot.py` — live framebuffer capture (panel is BGRX, not RGBX).
- `S99zz_lucynest` — boot hook fixes (see below).

Tests: 51 pre-existing + 48 new = 99, all passing.
`test_native_execute.py`, `test_action_schema.py`, `test_authorization.py`,
`test_hid.py`, `test_capture.py`, `test_boot_script.py`.

Seven real defects were found by adversarial verification after every worker
reported clean; details are in `.unlazy/lucynest-input-bridge/PLAN.md`
amendments (revisions 2 and 3). The most serious: a spent approval could be
replayed, and the execute happy path was unreachable.

No device, firmware, gadget, or boot change is part of the software phase
except the boot hook below.

## Device findings

### Touch works

- `/dev/input/event0` = `ns2009`.
- A 15-minute raw capture during owner taps produced `BTN_TOUCH` down/up,
  `ABS_X`/`ABS_Y`, and `SYN_REPORT` events.
- The ns2009 IRQ counter moved from 0 to 27/6 during the taps.
- The native client decoded the taps (`touch: ok` via the control socket).

**Conclusion: the touch sense path is functional.** No driver or hardware work
is required to get events.

### Calibration was the real touch fault

The saved matrix was degenerate:

```
[[0.3065, 2.4691, -9210.3360],
 [-0.0633, 0.0,     324.1772]]
```

The `0.0` on `raw_y` means vertical position was ignored, and a tap at raw
(2015, 2143) mapped to x ≈ −3301 — far off-screen, so no hitbox could ever
match. This is why buttons did not respond even though taps decoded.

Preserved on device as `calibration.json.bad-20260930`. Recalibration is
pending; it needs the panel to be visible.

### Display is frozen on the boot logo

Established by direct measurement:

- `fb0` receives correct content from the native client (verified by capture).
- `fb1`, `fb2`, `fb3` were cleared to fully transparent `(0,0,0,0)`.
- Pushing a solid full-screen colour to `fb0` through `cmd_jpeg_display`
  (exit 0) did **not** change the panel.
- The owner confirmed the panel still shows the Creality logo.

Root-cause indicators:

- `/sys/module/soc_fb/parameters/mixer_enable` was `0`.
- `/sys/module/soc_fb/parameters/lcd_is_inited` was `0`.
- Setting both to `1` did not start frame output; `layer0_frames` stayed at 2.
- `FBIOPAN_DISPLAY` is unsupported: `jzfb: not support this cmd: 460a`.
  `fb0` `virtual_size=480,544` (double-buffered) but panning is not available.
- `cmd_jpeg_display` opens `/dev/fb0` and calls `fb_open`/`fb_enable`/
  `fb_pan_display`, implemented in `/usr/lib/libhardware2.so`.
- Stock `display-server` also targets `/dev/fb0`; `boot_display` targets
  `/dev/fb1`.

Available control surface on `/sys/module/soc_fb/parameters/`:
`mixer_enable`, `use_default_order`, `layer0-3_enable/alpha/frames`,
`user_fb0-3_enable/xpos/ypos/width/height/scaling_*`, `srdma_enable`,
`is_rotated`, `rotator_angle`.

Unresolved: what actually commits a frame to the panel. The next step is to
decode the `libhardware2.so` ioctls (binaries pulled to the laptop) and/or
reproduce the stock boot order so the display is initialised before the native
client takes over.

## Boot hook changes (deployed)

`/etc/init.d/S99zz_lucynest`, deployed sha256
`5f82137b638efc57abe4f0c12607d967091c8a5ac60332d4971ec0327c332ba3`:

- Clears **all** overlay framebuffers (`fb1`, `fb2`, `fb3`), not just `fb1`.
  The logo occupied `fb2`/`fb3` as well.
- `force_home()` is skipped when `calibration.json` is absent, so the one-time
  calibration screen is no longer overridden at boot.
- Backups are written to `/root/lucy-nest/backups/`, never into `/etc/init.d`.

Device-side cleanup performed:

- `/etc/init.d/S99zz_lucynest.bak.overlayfix` **moved out of `/etc/init.d`**
  to `/root/lucy-nest/backups/`. `rcS` executes every `S??*` file, so that
  stray backup was being run as an init script on every boot.
- Prior deployed hook preserved as
  `/root/lucy-nest/backups/S99zz_lucynest.before-overlay-fix`.
- Stale legacy `/root/lucy-nest/client.pid` removed.

## Current device state at checkpoint

- Full stock Creality stack running for a display test:
  `master-server`, `app-server`, `display-server`, `Monitor`.
- Native client **stopped**.
- `mixer_enable=1`, `lcd_is_inited=1` (set manually; not persistent).
- No calibration file (bad one preserved as `.bad-20260930`).
- `/etc/init.d` contains only `S99mdns`, `S99start_app`, `S99zz_lucynest`.

## How to return to the native client

```sh
ssh lucy-nest
/etc/init.d/S99start_app stop
cd /root/lucy-nest/native
/etc/init.d/S99zz_lucynest restart
```

## Open items

1. **Display**: find what commits a frame to the panel; get the native UI
   visible. Blocks calibration and all touch UI work.
2. **Calibration**: after the panel is visible, re-run the 3-point calibration
   and verify every button.
3. **Touch gate**: not a hardware fault. The remaining work is calibration and
   hitbox verification.
4. **USB HID gate**: unverified. Kernel HID gadget support exists
   (`hidg_alloc`, `hidg_bind`, `hidg_setup`, `ghid_setup`), but no connector is
   confirmed to reach the OTG controller in device mode. Needs board/connector
   photos. Never use a plain USB-A-to-A cable between powered hosts.
5. **PC capture**: interface done; real Wayland-portal capture needs the PC
   side and owner consent.
6. **Boot hook reorder**: likely required — let the display initialise before
   the native client takes the framebuffer.

## Safety notes

- No firmware was flashed and no rootfs was overwritten.
- No USB gadget was bound; no OTG mode was forced.
- All display work is reversible with a reboot.
- Nothing has been committed to the device's own filesystem as boot state
  beyond the boot hook above.
