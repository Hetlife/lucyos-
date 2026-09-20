"""Generate deterministic 480x272 Little Lucy eye animation frames.

Lucy is white-only on near-black; red is reserved for semantic text/highlights.
No network or model dependency is required at runtime.
"""
from __future__ import annotations

from pathlib import Path
import argparse
import math
from PIL import Image, ImageDraw, ImageFont

W, H = 480, 272
BG = (9, 10, 9)
WHITE = (242, 239, 230)
RED = (227, 58, 53)
GREY = (102, 104, 101)
STATES = ("READY", "THINKING", "WORKING", "VERIFY", "SUCCESS", "NEEDS_YOU", "OFFLINE")
FRAMES = 12
def _font(size: int):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _eye_params(state: str, i: int):
    phase = 2 * math.pi * i / FRAMES
    blink = 1.0
    if state == "READY" and i in (9, 10): blink = 0.22 if i == 9 else 0.55
    if state == "THINKING": blink = 0.82 + 0.12 * math.sin(phase)
    if state == "WORKING": blink = 0.9 + 0.08 * math.sin(phase * 2)
    if state == "VERIFY": blink = 0.96
    if state == "SUCCESS": blink = 1.0 + 0.04 * math.sin(phase)
    if state == "NEEDS_YOU": blink = 1.02
    if state == "OFFLINE": blink = 0.28
    look = 0
    if state in ("THINKING", "WORKING", "VERIFY"):
        look = int(24 * math.sin(phase))
    return blink, look


def render_frame(state: str, i: int) -> Image.Image:
    scale = 3
    img = Image.new("RGB", (W*scale, H*scale), BG)
    d = ImageDraw.Draw(img)
    blink, look = _eye_params(state, i)
    cx, cy = 240*scale, 126*scale
    ew, eh = 300*scale, int(112*scale*blink)
    # Long-form hand-drawn aperture: two restrained white curves.
    top, bottom = [], []
    for n in range(81):
        t = n / 80
        x = cx - ew/2 + ew*t
        amp = math.sin(math.pi*t) ** 0.78
        top.append((x, cy - (eh/2)*amp))
        bottom.append((x, cy + (eh/2)*amp))
    d.line(top, fill=WHITE, width=5*scale, joint="curve")
    d.line(bottom, fill=WHITE, width=5*scale, joint="curve")

    # Subtle ribbed side structure from the original Lucy sketch language.
    for side in (-1, 1):
        base = cx + side*(ew/2 - 10*scale)
        for k in range(4):
            inset = k*7*scale
            yspan = max(12*scale, eh/2 - k*5*scale)
            d.line((base-side*inset, cy-yspan, base-side*inset, cy+yspan),
                   fill=WHITE, width=max(2, (3-k//2)*scale))

    # White iris and pupil; Lucy itself never uses semantic red.
    iris_r = int(min(46*scale, max(13*scale, eh*0.34)))
    px = cx + look*scale
    d.ellipse((px-iris_r, cy-iris_r, px+iris_r, cy+iris_r), outline=WHITE, width=4*scale)
    pupil_r = max(5*scale, int(iris_r*0.34))
    d.ellipse((px-pupil_r, cy-pupil_r, px+pupil_r, cy+pupil_r), fill=WHITE)

    # Sparse interface typography: identity in white, state as red emphasis.
    f_small, f_state = _font(12*scale), _font(16*scale)
    d.text((24*scale, 225*scale), "LUCY", font=f_small, fill=WHITE)
    label = state.replace("_", " ")
    box = d.textbbox((0, 0), label, font=f_state)
    tw = box[2] - box[0]
    d.text(((456*scale)-tw, 220*scale), label, font=f_state, fill=RED)
    return img.resize((W, H), Image.Resampling.LANCZOS)
def generate(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for state in STATES:
        d = out_dir / state.lower()
        d.mkdir(parents=True, exist_ok=True)
        for i in range(FRAMES):
            render_frame(state, i).save(d / f"{i:02d}.jpg", "JPEG", quality=90, optimize=True)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("out_dir", type=Path)
    p.add_argument("--state", choices=STATES)
    p.add_argument("--frame", type=int, default=0)
    p.add_argument("--single", type=Path)
    args = p.parse_args()
    if args.single:
        state = args.state or "READY"
        render_frame(state, args.frame % FRAMES).save(args.single, "JPEG", quality=92)
    else:
        generate(args.out_dir)


if __name__ == "__main__":
    main()
