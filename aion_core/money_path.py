"""The money path: for each project, the ordered real-world steps to real money,
which of them need the owner, and which are already done — measured, not
asserted.

Each project may carry `PROJECTS/<project>/money_path.json`:

  {"project": "...", "steps": [
      {"id": "s1", "title": "...", "you": "what the owner does, or empty if the system does it",
       "how": "where / which command", "checks": [ {...}, ... ]}
  ]}

A step is DONE when every check passes.  Checks are deterministic and read
real state:

  {"file": "relative/path"}                       file exists and is non-empty
  {"file_contains": ["relative/path", "text"]}    file contains the text
  {"experiment": ["EXP-001", "sent", ">=", 30]}   a field of experiments.status()
  {"milestone": "M0"}                             milestones.check()[M0].reached
  {"secret": "NAME"}                              the secret store has NAME
  {"meta": ["key", "value"]}                      db meta key equals value

The first step that is not DONE is NEXT; everything after it is LATER.  A NEXT
step with a non-empty `you` is the one thing the owner has to do right now —
that is what the phone shows first.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import bootstrap, db, experiments, milestones

STATUSES = ("DONE", "NEXT", "LATER")


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _paths() -> list[Path]:
    base = experiments.root()
    if not base.is_dir():
        return []
    return sorted(base.glob("*/money_path.json"))


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve(rel: str) -> Path:
    p = Path(rel)
    if p.is_absolute():
        return p
    # Experiment folders are under the same root as the money path itself, so a
    # test tree and the real repo both resolve without special cases.
    candidate = experiments.root().parent / rel
    return candidate if candidate.exists() else repo_root() / rel


_OPS = {
    ">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b, ">": lambda a, b: a > b,
    "<": lambda a, b: a < b, "=": lambda a, b: a == b, "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b, "in": lambda a, b: a in b,
}


def check(spec: dict) -> tuple[bool, str]:
    """Evaluate one check.  Returns (passed, human detail).  Never raises."""
    try:
        if "file" in spec:
            p = _resolve(spec["file"])
            ok = p.is_file() and p.stat().st_size > 0
            return ok, f"{spec['file']} {'exists' if ok else 'missing'}"
        if "file_contains" in spec:
            rel, text = spec["file_contains"]
            p = _resolve(rel)
            ok = p.is_file() and text in p.read_text(encoding="utf-8", errors="replace")
            return ok, f"{rel} {'contains' if ok else 'does not contain'} {text!r}"
        if "experiment" in spec:
            exp_id, field, op, value = spec["experiment"]
            s = experiments.status(exp_id)
            actual = s.get(field)
            ok = bool(_OPS[op](actual, value))
            return ok, f"{exp_id}.{field}={actual!r} (need {op} {value!r})"
        if "milestone" in spec:
            m = milestones.check().get(spec["milestone"], {})
            return bool(m.get("reached")), f"{spec['milestone']}: {m.get('evidence', 'unknown')}"
        if "secret" in spec:
            ok = bootstrap.has_secret(spec["secret"])
            return ok, f"secret {spec['secret']} {'set' if ok else 'not set'}"
        if "meta" in spec:
            key, value = spec["meta"]
            actual = db.get_meta(key, "")
            return actual == value, f"{key}={actual!r}"
        return False, f"unknown check {sorted(spec)}"
    except Exception as exc:  # a broken check must read as "not done", never crash status
        return False, f"check failed: {exc.__class__.__name__}: {exc}"


def project_status(path: Path) -> dict:
    doc = _load(path)
    steps = []
    next_seen = False
    for raw in doc.get("steps", []):
        results = [check(c) for c in raw.get("checks", [])]
        done = bool(results) and all(ok for ok, _ in results)
        if done:
            status = "DONE"
        elif not next_seen:
            status, next_seen = "NEXT", True
        else:
            status = "LATER"
        steps.append({
            "id": raw.get("id"), "title": raw.get("title", ""), "you": raw.get("you", ""),
            "how": raw.get("how", ""), "status": status,
            "needs_owner": bool(raw.get("you")),
            "detail": "; ".join(d for _, d in results) or "no check — never auto-done",
        })
    nxt = next((s for s in steps if s["status"] == "NEXT"), None)
    owner_next = next((s for s in steps if s["status"] != "DONE" and s["needs_owner"]), None)
    return {
        "project": doc.get("project", path.parent.name),
        "goal": doc.get("goal", ""),
        "steps": steps,
        "done": sum(1 for s in steps if s["status"] == "DONE"),
        "total": len(steps),
        "next": nxt,
        "owner_next": owner_next,
    }


def all_status() -> list[dict]:
    out = []
    for p in _paths():
        try:
            out.append(project_status(p))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            out.append({"project": p.parent.name, "goal": "", "steps": [], "done": 0,
                        "total": 0, "next": None, "owner_next": None,
                        "error": f"{p}: {exc}"})
    return out


def owner_line() -> str | None:
    """The one sentence the owner needs: what only they can do next."""
    for proj in all_status():
        if proj.get("owner_next"):
            s = proj["owner_next"]
            return f"Needs you ({proj['project']}): {s['you']}"
    return None


def report(project: str | None = None) -> str:
    lines = []
    for proj in all_status():
        if project and proj["project"] != project:
            continue
        lines.append(f"MONEY PATH — {proj['project']} ({proj['done']}/{proj['total']} done)")
        if proj.get("goal"):
            lines.append(proj["goal"])
        if proj.get("error"):
            lines.append(f"  error: {proj['error']}")
        for s in proj["steps"]:
            mark = {"DONE": "[x]", "NEXT": "[>]", "LATER": "[ ]"}[s["status"]]
            who = "YOU" if s["needs_owner"] else "system"
            lines.append(f"{mark} {s['id']} ({who}) {s['title']}")
            if s["status"] != "DONE" and s["you"]:
                lines.append(f"      do: {s['you']}")
            if s["status"] == "NEXT" and s["how"]:
                lines.append(f"      how: {s['how']}")
            if s["status"] != "DONE":
                lines.append(f"      check: {s['detail']}")
        lines.append("")
    return "\n".join(lines).rstrip() or "no money path defined — add PROJECTS/<project>/money_path.json"
