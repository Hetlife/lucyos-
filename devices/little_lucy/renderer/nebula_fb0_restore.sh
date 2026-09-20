#!/bin/sh
# Emergency and timed restore for the 15-second physical proof.
backup=/tmp/lucy-fb0-backup.raw
[ -f "$backup" ] && [ "$(wc -c < "$backup")" -eq 1044480 ] && dd if="$backup" of=/dev/fb0 bs=1920 count=544 2>/tmp/lucy-fb0-restore-dd.log
[ -r /tmp/lucy-display.pid ] && kill -CONT "$(cat /tmp/lucy-display.pid)" 2>/dev/null
[ -r /tmp/lucy-monitor.pid ] && kill -CONT "$(cat /tmp/lucy-monitor.pid)" 2>/dev/null
if ! pidof display-server >/dev/null 2>&1; then
    TSLIB_CONFFILE=/etc/ts.conf TSLIB_TSDEVICE=/dev/input/event0 TSLIB_FBDEVICE=/dev/fb0 TSLIB_PLUGINDIR=/usr/lib/ts HOME=/root /usr/bin/display-server >/tmp/lucy-display-restart.log 2>&1 &
fi
if ! pidof Monitor >/dev/null 2>&1; then
    HOME=/root /usr/bin/Monitor >/tmp/lucy-monitor-restart.log 2>&1 &
fi
