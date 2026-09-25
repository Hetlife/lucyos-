# Lucy-Nest resume checkpoint — 2026-09-26

## Current outcome

- Native Lucy-Nest is the **default boot display**: the red eye animation
  starts automatically after boot, with the page left on `home`.
- The stock Creality `display-server` and `Monitor` are stopped by the new
  boot hook.
- SSH remote control works, including owner-approved approval verbs.
- Touch is **not functional**; Gate 1 shows the NS2009 controller sees no
  touch pressure and taps generate no IRQ. This is a hardware/controller
  fault, not a UI, parser, calibration, or display fault.

## Repository state

- Worktree: `/home/scs-admin01/lucyos-worktrees/lucynest-source-reconciliation-20260925`
- Branch: `task/lucynest-source-reconciliation-20260925`
- Local commits (not pushed):
  - `b225687` chore: mark Lucy-Nest boot script executable
  - `9803d6d` nebula/native: default boot display to Lucy-Nest home animation
  - `3b50947` nebula/native: fix render block dedent outside main loop; add AST regression test
  - `821ebc1` nebula/native: make remote status open the Status page; add snapshot-only info verb
  - `4402f65` nebula/native: root-only unix-socket remote navigation; decisions gated off
  - `9a28c9d` fix: guard native touch runtime and status
  - `4787f44` fix: harden Nebula touch event decoding
  - `01c8af5` feat: reconcile native Lucy-Nest source
- `git status` shows only the pre-existing untracked `.unlazy/` directory.

## Live Nebula state (snapshot at 2026-09-26 02:55 IST)

- Host: `root@192.168.31.122`, SSH key
  `/home/scs-admin01/.ssh/little_lucy_nebula_rsa`, options
  `IdentitiesOnly=yes`, `IdentityAgent=none`,
  `PubkeyAcceptedAlgorithms=+ssh-rsa`, `BatchMode=yes`.
- Native client PID: `1459` (`/usr/bin/python3 /root/lucy-nest/native/client.py`).
- Deployed `client.py` sha256:
  `7316bc1489acbce101d2a456e274704b25b6070b1b59258651d6605e96a80951`
- Deployed `lucynest_ctl.py` sha256:
  `94c432bc7240166e1608ae764e93dd99c3c5681ff9b24a62be2ee9a46ee22e20`
- Boot hook: `/etc/init.d/S99zz_lucynest`, mode `0755`, md5
  `1712fbe49b15aaaa6b2f5592f7997449`, sorts after `S99start_app`.
- Control socket: `/run/lucy-nest/control.sock`, mode `0600`; directory
  `/run/lucy-nest` mode `0700`.
- Decision gate: `/root/lucy-nest/native/remote-decisions.enabled`, mode
  `0600`, first line `ALLOW_REMOTE_DECISIONS`.
- Last `info` output:
  `{"ok": true, "page": "home", "index": 0, "approvals": 2, "focused_id": "A-104", "online": true, "touch": "ok", "remote_decisions": true}`.
  The `touch: ok` snapshot is not proof of working physical touch; taps
  still produce no usable frames.

## What works

- Default boot display: native eye animation on `home`.
- SSH navigation over the root-only Unix socket:
  - `info` — snapshot only, no page change
  - `status` — opens the Status page and returns a snapshot
  - `home`, `inbox`, `next`, `review`, `detail_next`, `review_back`
- SSH approvals (owner-enabled):
  - navigate to the intended item (`inbox`, `next`, `info`, `review`)
  - `approve` or `deny`
  - `send` submits through the existing canonical bridge/Aion path
  - approvals are disabled by default and require the root-owned gate file
- Laptop bridge remains untouched and healthy.

Disable approvals immediately with:

```sh
ssh lucy-nest 'rm -f /root/lucy-nest/native/remote-decisions.enabled'
```

## Touch diagnosis

- `/dev/input/event0` is the NS2009 node; the client fd matches it; no
  `EVIOCGRAB`; no competing reader.
- Native client, stock display, warm reboot, cold power cycle, and a normal
  module reload attempt all failed to restore touch.
- Gate 1 read-only I²C probe results:
  - `0xE0` (pressure gate) was `0x0000` across 60+ samples, tapped and
    untapped; never reached the driver's `0x50` threshold.
  - `0xC0` returned `0xf0ff`; `0xD0` returned `0x0000`.
  - Read-only I²C reads caused IRQ 74 activity; physical taps produced
    zero IRQ.
  - No `Poll touch data failed` dmesg entries.
- Conclusion: the NS2009 ACKs and its register interface responds, but the
  touch-sense path reports no pressure. Likely panel/flex/connector or
  controller input fault. A patched vendor driver would read the same
  `0xE0 = 0x0000`.

Vendor module facts recovered earlier:

- Module: `/module_driver/ns2009_touch.ko`, loader
  `insmod ns2009_touch.ko i2c_bus_num=4`.
- Vermagic: `4.4.94 SMP preempt mod_unload MIPS32_R2 32BIT`.
- Only parameter: `i2c_bus_num`.
- `Unbalanced enable for IRQ 74` and the spurious counter are cosmetic;
  the report gate/read path is the likely software area, but hardware
  pressure is absent first.

## Next steps

1. **Hardware first:** inspect/replace the touch flex, connector, panel,
   or controller. Re-run `i2cget -y -f 4 0x48 0xE0 w` while pressing after
   repair; expect a nonzero value and IRQ activity.
2. If hardware is ruled out, pursue the vendor-driver path:
   - obtain the Creality/Ingenic BSP kernel headers for 4.4.94 and the
     GCC 7.2 MIPS32R2 xburst2 toolchain;
   - rebuild the reconstructed `ns2009_touch` source with a diagnostic
     log of `0xE0/0xC0/0xD0`, then a minimal read/report fix;
   - validate vermagic and struct offsets before loading a staged module
     from `/tmp` (never overwrite `/module_driver` without a backup/approval).
3. If no toolchain is available, consider a userspace `i2c-4` to
   `/dev/uinput` bridge after `rmmod ns2009_touch` (requires
   `CONFIG_INPUT_UINPUT` and explicit owner approval).
4. Clean up the stale legacy file `/root/lucy-nest/client.pid` (points at a
   dead PID; the native boot script uses `/root/lucy-nest/native/client.pid`).

## Recovery artifacts and re-extraction

The reverse-engineering artifacts were in `/tmp/opencode/ns2009/` and have
been cleaned. The stock OTA images remain available:

- `/home/scs-admin01/LucyOS-Recovery/Nebula-NPad01/NEBULA_ota_img_V1.1.0.23.img`
- `/home/scs-admin01/LucyOS-Recovery/Nebula-NPad01/NEBULA_ota_img_V6.1.0.23.img`
- `/home/scs-admin01/LucyOS-Recovery/Nebula-NPad01/nebula-pad-firmware-customizer/firmware/NEBULA_ota_img_V1.1.0.23.img`

Re-extract the rootfs and module from the OTA image before driver work.

## Rollback

Remove the default native boot display:

```sh
rm -f /etc/init.d/S99zz_lucynest
kill "$(cat /root/lucy-nest/native/client.pid)"
setsid /usr/bin/display-server >/dev/null 2>&1 </dev/null &
setsid /usr/bin/Monitor >/dev/null 2>&1 </dev/null &
```

Start the native client manually:

```sh
cd /root/lucy-nest/native
LUCY_NEST_RUNTIME=nebula LUCY_NEST_DISPLAY_OWNER=confirmed \
  setsid /usr/bin/python3 /root/lucy-nest/native/client.py >>client.log 2>&1 </dev/null &
echo $! > /root/lucy-nest/native/client.pid
/usr/bin/python3 /root/lucy-nest/native/lucynest_ctl.py home
```

## Safety boundaries still in force

- No firmware flashing or rootfs overwrite without a new explicit owner
  decision.
- No driver unbind/rebind, sysfs writes, or module loading outside an
  approved staged test.
- No bridge or canonical Aion state changes from this work.
- Native boot hook is the only boot change; rollback is documented above.
- WhatsApp remains the primary owner channel; SSH approvals are the
  owner-approved secondary surface.
