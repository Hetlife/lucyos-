"""Local-model (Ollama) capacity.

Reuses `worker.ollama_available()` rather than re-implementing an HTTP probe —
the worker loop is the existing source of truth for whether class A execution
is possible on this machine.  This module only adds the capacity signals the
Resource Governor needs on top: queue depth and free RAM.
"""
from __future__ import annotations

from pathlib import Path


def _lazy_imports():
    # Imported lazily to avoid a resource_governor -> worker -> resource_governor
    # cycle if worker.py ever imports this package directly.
    from ... import worker, db, tasks
    return worker, db, tasks


def read() -> dict:
    worker, db, tasks = _lazy_imports()
    available = worker.ollama_available()
    counts = tasks.counts()
    queue_depth = counts.get("CLAIMED", 0) + counts.get("RUNNING", 0)
    return {
        "provider": "local",
        "available": available,
        "model": db.get_meta("ollama_model", "llama3.1:8b"),
        "queue_depth": queue_depth,
        "ram_available_mb": _ram_available_mb(),
        "source": "worker.ollama_available + /proc/meminfo" if available else "worker.ollama_available",
        "confidence": "LOCAL_OBSERVED" if available else "LOCAL_OBSERVED",
    }


def _ram_available_mb() -> int | None:
    """Best-effort, Linux-only, stdlib-only.  None everywhere else — never guessed."""
    meminfo = Path("/proc/meminfo")
    if not meminfo.exists():
        return None
    try:
        for line in meminfo.read_text(encoding="utf-8").splitlines():
            if line.startswith("MemAvailable:"):
                kb = int(line.split()[1])
                return kb // 1024
    except (OSError, ValueError, IndexError):
        return None
    return None
