"""Generate expressive 480x272 Lucy-Nest animation frames.

Design rules: near-black field, Lucy character in warm white only, semantic
red reserved for status text. Renderer is deterministic and offline.
"""
from __future__ import annotations

from pathlib import Path
import argparse
import math
from PIL import Image, ImageDraw, ImageFont

W, H = 480, 272
SCALE = 3
BG = (7, 8, 8)
WHITE = (244, 241, 232)
SOFT = (178, 178, 171)
RED = (227, 58, 53)
STATES = ("READY", "THINKING", "WORKING", "VERIFY", "SUCCESS", "NEEDS_YOU", "OFFLINE")
FRAMES = 18


def _font(size: int):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _motion(state: str, i: int):
    phase = 2 * math.pi * i / FRAMES
    blink = 1.0
    if state == "READY" and i in (13, 14):
        blink = 0.16 if i == 13 else 0.55
    elif state == "THINKING":
        blink = 0.92 + 0.05 * math.sin(phase * 2)
    elif state == "WORKING":
        blink = 0.88 + 0.08 * math.sin(phase * 3)
    elif state == "VERIFY":
        blink = 0.72 + 0.03 * math.sin(phase)
    elif state == "SUCCESS":
        blink = 0.96 + 0.04 * math.sin(phase)
    elif state == "NEEDS_YOU":
        blink = 1.02
    elif state == "OFFLINE":
        blink = 0.24

    look_x = 0.0
    look_y = 0.0
    if state == "THINKING":
        look_x = 14 * math.sin(phase)
        look_y = -5 * math.cos(phase * 0.5)
    elif state == "WORKING":
        look_x = 8 * math.sin(phase * 2)
    elif state == "VERIFY":
        look_x = 3 * math.sin(phase)
    return blink, look_x, look_y, phase


def _path_eye(d, cx, cy, width, height, stroke):
    top = []
    bottom = []
    for n in range(101):
        t = n / 100
        x = cx - width / 2 + width * t
        amp = math.sin(math.pi * t) ** 0.72
        pinch = 0.92 + 0.08 * math.cos(2 * math.pi * t)
        top.append((x, cy - (height / 2) * amp * pinch))
        bottom.append((x, cy + (height / 2) * amp * pinch))
    d.line(top, fill=WHITE, width=stroke, joint="curve")
    d.line(bottom, fill=WHITE, width=stroke, joint="curve")


def _draw_ribs(d, cx, cy, width, height):
    for side in (-1, 1):
        anchor = cx + side * (width / 2 - 6 * SCALE)
        for k in range(5):
            x = anchor - side * k * 6 * SCALE
            span = max(13 * SCALE, height / 2 - k * 5 * SCALE)
            alpha = 255 - k * 28
            c = tuple(int(v * alpha / 255) for v in WHITE)
            d.line((x, cy - span, x, cy + span), fill=c,
                   width=max(2, (4 - k // 2) * SCALE))


def _draw_face(d, state, blink, look_x, look_y, phase):
    cx, cy = 240 * SCALE, 118 * SCALE
    width = 314 * SCALE
    height = max(18 * SCALE, int(116 * SCALE * blink))
    _path_eye(d, cx, cy, width, height, 5 * SCALE)
    _draw_ribs(d, cx, cy, width, height)

    sep = 54 * SCALE
    eye_w = 54 * SCALE
    eye_h = max(10 * SCALE, int(58 * SCALE * blink))
    if state == "SUCCESS":
        eye_h = int(44 * SCALE)
    if state == "OFFLINE":
        eye_h = 11 * SCALE

    for side in (-1, 1):
        ex = cx + side * sep + look_x * SCALE
        ey = cy + look_y * SCALE
        box = (ex-eye_w/2, ey-eye_h/2, ex+eye_w/2, ey+eye_h/2)
        d.rounded_rectangle(box, radius=max(5*SCALE, eye_h/2), outline=WHITE, width=4*SCALE)
        if state == "SUCCESS":
            y = ey + 4*SCALE
            d.arc((ex-eye_w/2, y-eye_h/2, ex+eye_w/2, y+eye_h/2), 195, 345,
                  fill=WHITE, width=4*SCALE)
        else:
            pr = max(4*SCALE, int(min(eye_h, eye_w) * 0.16))
            px = ex + side * 2*SCALE
            py = ey
            d.ellipse((px-pr, py-pr, px+pr, py+pr), fill=WHITE)

    if state == "WORKING":
        y = 187 * SCALE
        span = 84 * SCALE
        for j in range(7):
            x = cx - span/2 + j*(span/6)
            h = (7 + 7*abs(math.sin(phase + j*0.7))) * SCALE
            d.line((x, y-h/2, x, y+h/2), fill=SOFT, width=2*SCALE)
    elif state == "VERIFY":
        d.arc((cx-38*SCALE, cy-38*SCALE, cx+38*SCALE, cy+38*SCALE),
              -70, 70, fill=SOFT, width=2*SCALE)


def render_frame(state: str, i: int) -> Image.Image:
    img = Image.new("RGB", (W*SCALE, H*SCALE), BG)
    d = ImageDraw.Draw(img)
    blink, look_x, look_y, phase = _motion(state, i)
    _draw_face(d, state, blink, look_x, look_y, phase)

    f_small = _font(12*SCALE)
    f_state = _font(16*SCALE)
    d.text((24*SCALE, 225*SCALE), "LUCY", font=f_small, fill=WHITE)
    label = state.replace("_", " ")
    box = d.textbbox((0, 0), label, font=f_state)
    tw = box[2] - box[0]
    d.text(((456*SCALE)-tw, 220*SCALE), label, font=f_state, fill=RED)
    return img.resize((W, H), Image.Resampling.LANCZOS)


def generate(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for state in STATES:
        folder = out_dir / state.lower()
        folder.mkdir(parents=True, exist_ok=True)
        for i in range(FRAMES):
            render_frame(state, i).save(folder / f"{i:02d}.jpg", "JPEG", quality=92, optimize=True)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("out_dir", type=Path)
    p.add_argument("--state", choices=STATES)
    p.add_argument("--frame", type=int, default=0)
    p.add_argument("--single", type=Path)
    args = p.parse_args()
    if args.single:
        render_frame(args.state or "READY", args.frame % FRAMES).save(args.single, "JPEG", quality=94)
    else:
        generate(args.out_dir)


if __name__ == "__main__":
    main()
