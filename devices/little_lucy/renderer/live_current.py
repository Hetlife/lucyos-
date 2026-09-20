#!/usr/bin/env python3
"""Publish the current Little Lucy JPEG from sanitized state.json."""
from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUNTIME = ROOT / "runtime" / "little-lucy"
STATE = RUNTIME / "state.json"
FRAMES = RUNTIME / "frames"
CURRENT = RUNTIME / "current.jpg"
TMP = RUNTIME / ".current.jpg.tmp"
FPS = 5

MAP = {
    "READY": "ready", "IDLE": "ready", "LISTENING": "listening",
    "THINKING": "thinking", "WORKING": "working", "VERIFY": "verify",
    "CHECKING": "verify", "SUCCESS": "success", "NEEDS_YOU": "needs_you",
    "NEEDS-ATTENTION": "needs_you", "WARNING": "needs_you",
    "CRITICAL": "needs_you", "OFFLINE": "offline", "RECONNECTING": "offline",
}

def read_state() -> str:
    try:
        payload = json.loads(STATE.read_text())
        return MAP.get(str(payload.get("state", "READY")).upper(), "ready")
    except Exception:
        return "offline"


def publish(src: Path) -> None:
    shutil.copyfile(src, TMP)
    os.replace(TMP, CURRENT)


def main() -> None:
    frame = 0
    RUNTIME.mkdir(parents=True, exist_ok=True)
    while True:
        state = read_state()
        folder = FRAMES / state
        src = folder / f"{frame % 12:02d}.jpg"
        if not src.exists():
            src = FRAMES / "offline" / "00.jpg"
        publish(src)
        frame += 1
        time.sleep(1 / FPS)


if __name__ == "__main__":
    main()
