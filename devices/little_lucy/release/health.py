"""Minimal candidate release health check."""
from pathlib import Path

assert (Path(__file__).parent.parent / "emulator/static/index.html").is_file()
