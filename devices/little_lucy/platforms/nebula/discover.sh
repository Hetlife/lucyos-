#!/bin/sh
# Read-only inventory. Run manually after authorized SSH access exists.
set -u
section() { printf '\n## %s\n' "$1"; }
section system
uname -a
cat /proc/cpuinfo 2>/dev/null
cat /proc/meminfo 2>/dev/null
section partitions_and_mounts
cat /proc/partitions 2>/dev/null
cat /proc/mounts 2>/dev/null
section init_and_services
ls -ld /sbin/init /etc/init.d /etc/systemd 2>/dev/null
ps 2>/dev/null
section graphics
ls -l /dev/fb* /dev/dri/* 2>/dev/null
cat /sys/class/graphics/fb*/name 2>/dev/null
ls /usr/lib/*EGL* /usr/lib/*GLES* /lib/*EGL* /lib/*GLES* 2>/dev/null
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
