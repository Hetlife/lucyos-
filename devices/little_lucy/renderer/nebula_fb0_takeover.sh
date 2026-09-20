#!/bin/sh
# Run on Nebula as root. Abort before signals/writes unless all guards pass.
set -eu
[ "$(cat /sys/class/graphics/fb0/virtual_size)" = 480,544 ]
[ "$(cat /sys/class/graphics/fb0/stride)" = 1920 ]
[ "$(cat /sys/class/graphics/fb0/bits_per_pixel)" = 32 ]
[ "$(wc -c < /tmp/lucy-proof.raw)" -eq 522240 ]
[ ! -e /tmp/lucy-fb0-backup.raw ] || { echo 'Existing backup: abort' >&2; exit 1; }
set -- $(pidof display-server); [ "$#" -eq 1 ]; display_pid=$1
set -- $(pidof Monitor); [ "$#" -eq 1 ]; monitor_pid=$1
command -v nohup >/dev/null
cat /tmp/lucy-proof.raw /tmp/lucy-proof.raw > /tmp/lucy-fb0-double.raw
[ "$(wc -c < /tmp/lucy-fb0-double.raw)" -eq 1044480 ]
dd if=/dev/fb0 of=/tmp/lucy-fb0-backup.raw bs=1920 count=544 2>/tmp/lucy-fb0-backup-dd.log
[ "$(wc -c < /tmp/lucy-fb0-backup.raw)" -eq 1044480 ]
printf '%s\n' "$display_pid" > /tmp/lucy-display.pid
printf '%s\n' "$monitor_pid" > /tmp/lucy-monitor.pid
nohup sh -c 'sleep 15; sh /tmp/nebula_fb0_restore.sh' </dev/null >/tmp/lucy-fb0-timer.log 2>&1 &
kill -STOP "$monitor_pid"
kill -STOP "$display_pid" || { kill -CONT "$monitor_pid"; exit 1; }
dd if=/tmp/lucy-fb0-double.raw of=/dev/fb0 bs=1920 count=544 2>/tmp/lucy-fb0-write-dd.log || sh /tmp/nebula_fb0_restore.sh
