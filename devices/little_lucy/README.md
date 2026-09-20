# Little Lucy preparation

This optional device endpoint consumes a sanitized LUCY_STATE v1 projection. AION remains the authority. The protocol allows only version, sequence, timestamp, state, and a short safe status. Never send secrets, raw logs, prompts, or camera frames. Face recognition cannot authorize consequential actions. Display operation needs no paid API.

## Local development

Run `python3 -m devices.little_lucy.ctl emulator`, then open `http://127.0.0.1:4872/` on Lucy-den. The frame is 480x272. The UI is black, Lucy is white, red marks semantic state, and one touch target is large. It shows RECONNECTING during transient failures and OFFLINE after 15 seconds. Touch has no consequential action yet. Run `python3 -m unittest discover -s devices/little_lucy/tests -v` for tests.

`little-lucyctl` provides status, doctor, discover, deploy, restart, logs, screenshot, rollback, hardware, camera, sensors, and emulator commands. Current deploy and rollback operate on a local root only. Remote commands report unavailable until inventory proves the service, graphics, camera, sensors, and screenshot routes.

## Release flow

`python3 -m devices.little_lucy.ctl --root <local-root> deploy devices/little_lucy <version>` copies into `releases/<version>`, runs `release/health.py`, atomically switches `current`, and retains `previous`. Activation health failure restores the old current release. `rollback` switches to previous. Versions are constrained and release directories are immutable. Future transport is Wi-Fi/SSH to an endpoint staging directory; that path has not been exercised. Do not repeatedly flash for application updates.

## Nebula discovery and recovery

The read-only `platforms/nebula/discover.sh` is for manual execution only after authorized SSH access exists. Capture its output on Lucy-den and inspect CPU, RAM, kernel, partitions, filesystem, init, graphics, input, Wi-Fi, USB, camera, sensor, services, storage, and network before selecting the renderer or enabling features. USB debugging is optional and unverified.

Recovery workspace: `/home/scs-admin01/LucyOS-Recovery/Nebula-NPad01`. Stock V1.1.0.23 image is present with SHA256 `9254cc4173aac58afeb9f571055367cb7e8fcc76f257abd378221530f5514309`. The custom V6.1.0.23 image was later found inside the customizer firmware directory and its SHA256 `fac10711000ba76207b445ad1776ed40dec42fb6a6fa5f5650cf03eb2f928e96` was verified; see live discovery below. Preserve stock untouched. Before a firmware write, verify the custom image, confirm the exact vendor recovery steps and media, and capture device-specific data if accessible. Expected result of a later approved update is a successful vendor update and restored network access; it has not been tested. On failure, use the proven vendor recovery procedure with the stock image. The actual button/USB/SD recovery sequence is still unknown.

## Live discovery, 2026-09-20

Lucy-den had `wlo1` at `192.168.31.125/24`; `192.168.31.122` replied to both ICMP probes. TCP 22, 80, and 9999 accepted connections. SSH exposed `SSH-2.0-dropbear_2019.78`; no authentication was attempted. HTTP `/` returned 200, the Creality web UI, and `httpd/1.23.7.4`. WebSocket `/` on 9999 returned HTTP 101 and sent status frames without an application command.

Passive WebSocket status reported `modelVersion` containing `DWIN hw ver:NEBULA` and `DWIN sw ver:6.1.0.23`. It also reported `model: Ender-3 Pro`, which is a printer model field, not proof that the pad model changed; `connect: 0`, `video: 0`, `video1: 0`, and `aiDetection: 0`. Camera or AI capability cannot be inferred from those flags. The historical local note said stock 1.1.0.23 and no custom flash. Current live version therefore conflicts with that historical note. The cause and timing are unknown; no SSH access or device storage inspection occurred in this discovery.

The custom V6.1.0.23 image was found at `nebula-pad-firmware-customizer/firmware/NEBULA_ota_img_V6.1.0.23.img`. Its SHA256 is `fac10711000ba76207b445ad1776ed40dec42fb6a6fa5f5650cf03eb2f928e96` (PASS). It is an encrypted 7-Zip archive with 119 entries; the customizer-derived archive key was used only in memory for `testzip()`, which returned no bad entry. The archive includes `ota_config.in` and `ota_v6.1.0.23/ota_update.in`. The customizer checkout is at `f4b82205171dd4f5817fc194c804b0e2a84e5015`; its code creates a V6 image from V1.1.0.23 by changing the root filesystem, OTA metadata, and packaging. This supports local provenance but does not establish that this exact image is installed on the device.

Both stock copies still hash to `9254cc4173aac58afeb9f571055367cb7e8fcc76f257abd378221530f5514309` (PASS). The available local README explains image creation but does not specify the exact Nebula update or physical recovery sequence. Recovery procedure remains **PARTIAL**: a validated stock artifact exists, but the device-specific restore method is unverified. Do not initiate a firmware write until the current live version discrepancy and recovery sequence are resolved.

## Measured hardware inventory, 2026-09-20

Owner supplied read-only terminal measurements: Buildroot 2020.02.1; Linux 4.4.94; Ingenic XBurst2/X2000 MIPS with two cores; about 197 MiB RAM plus 128 MiB swap; about 5.4 GiB free on `/usr/data`. `/dev/fb0` through `/dev/fb3` exist. fb0 is `jzfb`, reports `virtual_size=480,544` and 32 bits per pixel. The panel is 480x272. Double virtual height could be two page buffers, but this remains a hypothesis pending visible geometry, y-offset, stride and driver topology. NS2009 touchscreen is `/dev/input/event0`. `/dev/video0` through `/dev/video3` exist; no standard IIO device was returned. Python 3 exists. `/usr/bin/display-server` participates in the stock display stack. Python package filenames do not establish SDL or Qt runtime support.

**Display owner gate:** device nodes alone do not prove an unused visible layer. Before any physical render, capture per-framebuffer geometry and blank/state, fbset ioctl output, display-server descriptors/maps/linkage/startup, and layer topology. Determine pixel channel order and whether writes to fb1–fb3 are visible and independent. Preserve stock process and touch input. A direct framebuffer/layer writer is the preferred minimum renderer once ownership and restoration are proved. The local black/white proof asset is `renderer/proof.py`; it creates a 480x272, 32-bpp frame and never opens a device.

The proposed next action is running `sh devices/little_lucy/platforms/nebula/discover.sh` over owner-assisted password SSH and saving its output on Lucy-den. It only reads files and process state. No visible result is expected and no restoration is needed. A framebuffer write remains gated until a concrete target and exact restore sequence are established.
