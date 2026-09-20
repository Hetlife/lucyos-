#!/bin/sh
# Read-only inventory. Run manually after authorized SSH access exists.
set -u
section() { printf '\n## %s\n' "$1"; }
section system
uname -a
cat /etc/os-release /etc/issue 2>/dev/null
cat /proc/cpuinfo 2>/dev/null
cat /proc/meminfo 2>/dev/null
cat /proc/swaps 2>/dev/null
section partitions_and_mounts
cat /proc/partitions 2>/dev/null
cat /proc/mounts 2>/dev/null
section init_and_services
ls -ld /sbin/init /etc/init.d /etc/systemd 2>/dev/null
ps 2>/dev/null
section graphics
ls -l /dev/fb* /dev/dri/* 2>/dev/null
for fb in /sys/class/graphics/fb[0-9]*; do
    [ -d "$fb" ] || continue
    printf '\n%s\n' "$fb"
    for field in name modes mode virtual_size stride bits_per_pixel blank state rotate pan step; do
        [ -r "$fb/$field" ] && { printf '%s: ' "$field"; cat "$fb/$field"; }
    done
    ls -ld "$fb" "$fb/device" "$fb/subsystem" 2>/dev/null
done
cat /proc/fb 2>/dev/null
command -v fbset >/dev/null 2>&1 && fbset -i 2>/dev/null
ls -l /sys/class/graphics /sys/class/video4linux 2>/dev/null
cat /proc/cmdline /proc/iomem 2>/dev/null
ls /usr/lib/*EGL* /usr/lib/*GLES* /lib/*EGL* /lib/*GLES* 2>/dev/null
section display_owner
for p in /proc/[0-9]*; do
    [ -r "$p/comm" ] || continue
    name=$(cat "$p/comm" 2>/dev/null)
    case "$name" in *display*|*creality*|*klipper*) ;; *) continue ;; esac
    printf '\n%s %s\n' "$p" "$name"
    tr '\000' ' ' < "$p/cmdline" 2>/dev/null; printf '\n'
    ls -l "$p/exe" "$p/fd"/* 2>/dev/null
    cat "$p/maps" 2>/dev/null
done
ls -l /usr/bin/display-server /etc/init.d /etc/rc.d 2>/dev/null
command -v file >/dev/null 2>&1 && file /usr/bin/display-server 2>/dev/null
command -v readelf >/dev/null 2>&1 && readelf -d /usr/bin/display-server 2>/dev/null
command -v ldd >/dev/null 2>&1 && ldd /usr/bin/display-server 2>/dev/null
grep -R -l 'display-server' /etc/init.d /etc/rc.d /etc/inittab 2>/dev/null
section input_and_sensors
cat /proc/bus/input/devices 2>/dev/null
ls -l /dev/input/* /sys/bus/iio/devices/* 2>/dev/null
section wifi_usb_camera
ls -l /sys/class/net /sys/bus/usb/devices /dev/video* 2>/dev/null
section storage
df -h 2>/dev/null
section network
ip addr 2>/dev/null
ip route 2>/dev/null
