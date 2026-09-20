#!/usr/bin/env python3
import os, struct, time, urllib.request

DEVICE = "/dev/input/event0"
ENDPOINT = "http://192.168.31.125:18791/touch"
EV_SYN, EV_KEY, EV_ABS = 0, 1, 3
SYN_REPORT, BTN_TOUCH = 0, 330
ABS_X, ABS_Y = 0, 1
fmt = "llHHI"
size = struct.calcsize(fmt)
x = y = None
pressed = False
last_sent = 0.0

fd = os.open(DEVICE, os.O_RDONLY)
while True:
    data = os.read(fd, size)
    if len(data) != size:
        continue
    sec, usec, etype, code, value = struct.unpack(fmt, data)
    if etype == EV_ABS:
        if code == ABS_X: x = value
        elif code == ABS_Y: y = value
    elif etype == EV_KEY and code == BTN_TOUCH:
        pressed = bool(value)
    elif etype == EV_SYN and code == SYN_REPORT and x is not None and y is not None:
        now = time.time()
        if now - last_sent < 0.08:
            continue
        qs = f"?x={x}&y={y}&down={1 if pressed else 0}&raw=event0"
        try:
            urllib.request.urlopen(ENDPOINT + qs, timeout=0.5).read()
        except Exception:
            pass
        last_sent = now
