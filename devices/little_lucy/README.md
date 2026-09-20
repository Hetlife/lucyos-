# Little Lucy preparation

This optional device endpoint consumes a sanitized LUCY_STATE v1 projection. AION remains the authority. The protocol allows only version, sequence, timestamp, state, and a short safe status. Never send secrets, raw logs, prompts, or camera frames. Face recognition cannot authorize consequential actions. Display operation needs no paid API.

## Local development

Run `python3 -m devices.little_lucy.ctl emulator`, then open `http://127.0.0.1:4872/` on Lucy-den. The frame is 480x272. The UI is black, Lucy is white, red marks semantic state, and one touch target is large. It shows RECONNECTING during transient failures and OFFLINE after 15 seconds. Touch has no consequential action yet. Run `python3 -m unittest discover -s devices/little_lucy/tests -v` for tests.

`little-lucyctl` provides status, doctor, discover, deploy, restart, logs, screenshot, rollback, hardware, camera, sensors, and emulator commands. Current deploy and rollback operate on a local root only. Remote commands report unavailable until inventory proves the service, graphics, camera, sensors, and screenshot routes.

## Release flow

`python3 -m devices.little_lucy.ctl --root <local-root> deploy devices/little_lucy <version>` copies into `releases/<version>`, runs `release/health.py`, atomically switches `current`, and retains `previous`. Activation health failure restores the old current release. `rollback` switches to previous. Versions are constrained and release directories are immutable. Future transport is Wi-Fi/SSH to an endpoint staging directory; that path has not been exercised. Do not repeatedly flash for application updates.

## Nebula discovery and recovery

The read-only `platforms/nebula/discover.sh` is for manual execution only after authorized SSH access exists. Capture its output on Lucy-den and inspect CPU, RAM, kernel, partitions, filesystem, init, graphics, input, Wi-Fi, USB, camera, sensor, services, storage, and network before selecting the renderer or enabling features. USB debugging is optional and unverified.

Recovery workspace: `/home/scs-admin01/LucyOS-Recovery/Nebula-NPad01`. Stock V1.1.0.23 image is present with SHA256 `9254cc4173aac58afeb9f571055367cb7e8fcc76f257abd378221530f5514309`. The expected custom V6.1.0.23 image is absent, so SHA256 `fac10711000ba76207b445ad1776ed40dec42fb6a6fa5f5650cf03eb2f928e96` remains unverified. Preserve stock untouched. Before a firmware write, verify the custom image, confirm the exact vendor recovery steps and media, and capture device-specific data if accessible. Expected result of a later approved update is a successful vendor update and restored network access; it has not been tested. On failure, use the proven vendor recovery procedure with the stock image. The actual button/USB/SD recovery sequence is still unknown.
