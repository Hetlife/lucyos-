"""Prompt work orders backed by files, with LucyOS sessions as canonical execution history.

This is deliberately not another task queue. Prompt files are transport/provenance only.
"""
from __future__ import annotations

from pathlib import Path
import re

from . import security, sessions, util

PROMPT_RE = re.compile(r"^PRM-[A-F0-9]{8}$")
STATES = ("00_PENDING", "01_PROCESSING", "02_ARCHIVE")
ARCHIVE_OUTCOMES = {"SUCCESS", "NOOP", "REJECTED"}

def root() -> Path:
    p = Path(__file__).resolve().parents[1] / "prompts"
    for name in STATES:
        (p / name).mkdir(parents=True, exist_ok=True)
    return p

def _locations(prompt_id: str) -> list[tuple[str, Path]]:
    if not PROMPT_RE.match(prompt_id):
        raise ValueError("invalid prompt id")
    out = []
    for state in STATES:
        out.extend((state, p) for p in (root() / state).glob(prompt_id + "__*.md"))
    return out

def _find(prompt_id: str, state: str) -> Path:
    matches = _locations(prompt_id)
    if len(matches) != 1:
        raise ValueError(f"prompt {prompt_id} has {len(matches)} copies across lifecycle states")
    found_state, path = matches[0]
    if found_state != state:
        raise ValueError(f"prompt {prompt_id} is in {found_state}, expected {state}")
    return path

def status(prompt_id: str) -> dict:
    matches = _locations(prompt_id)
    if not matches:
        return {"prompt_id": prompt_id, "status": "MISSING", "path": None, "conflict": False}
    if len(matches) > 1:
        return {"prompt_id": prompt_id, "status": "CONFLICT", "path": None, "conflict": True,
                "locations": [{"state": s, "path": str(p)} for s, p in matches]}
    state, path = matches[0]
    return {"prompt_id": prompt_id, "status": state, "path": str(path), "conflict": False}

def _safe_title(title: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9._-]+", "-", title.strip()).strip("-.")[:80]
    return clean or "work-order"

def submit(title: str, body: str, *, project: str = "LucyOS") -> dict:
    if security.scan_text(body):
        raise ValueError("prompt contains credential-shaped content")
    prompt_id = util.new_id("PRM")
    path = root() / "00_PENDING" / f"{prompt_id}__{_safe_title(title)}.md"
    text = f"# PROMPT WORK ORDER\n\n- PROMPT-ID: {prompt_id}\n- STATUS: PENDING\n- PROJECT: {security.redact(project)}\n- CREATED-AT: {util.now()}\n- SESSION-ID: none\n\n## Objective\n{security.redact(title)}\n\n## Instructions\n{security.redact(body)}\n\n## Execution receipt\nNot yet used.\n"
    util.atomic_write(path, text)
    return {"prompt_id": prompt_id, "path": str(path), "status": "PENDING"}

def claim(prompt_id: str, *, actor: str, model: str = "", model_class: str = "B") -> dict:
    src = _find(prompt_id, "00_PENDING")
    session_id = sessions.start(actor, model=model, model_class=model_class, objective=f"Execute prompt work order {prompt_id}")
    text = src.read_text(encoding="utf-8")
    text = text.replace("- STATUS: PENDING", "- STATUS: PROCESSING", 1).replace("- SESSION-ID: none", f"- SESSION-ID: {session_id}", 1)
    dst = root() / "01_PROCESSING" / src.name
    util.atomic_write(dst, text)
    src.unlink()
    sessions.log(session_id, "start", f"Claimed {prompt_id}")
    return {"prompt_id": prompt_id, "session_id": session_id, "path": str(dst), "status": "PROCESSING"}

def archive(prompt_id: str, *, session_id: str, outcome: str, evidence: str, resume_point: str = "complete") -> dict:
    outcome = outcome.upper()
    if outcome not in ARCHIVE_OUTCOMES:
        raise ValueError("blocked/partial prompts must remain in PROCESSING")
    src = _find(prompt_id, "01_PROCESSING")
    text = src.read_text(encoding="utf-8")
    if f"- SESSION-ID: {session_id}" not in text:
        raise ValueError("session does not own this prompt")
    if not evidence.strip():
        raise ValueError("archive requires evidence")
    receipt = f"\n## Used / archive receipt\n- USED: yes\n- OUTCOME: {outcome}\n- SESSION-ID: {session_id}\n- ARCHIVED-AT: {util.now()}\n- EVIDENCE: {security.redact(evidence)}\n- RESUME-POINT: {security.redact(resume_point)}\n"
    text = text.replace("- STATUS: PROCESSING", "- STATUS: ARCHIVED", 1) + receipt
    dst = root() / "02_ARCHIVE" / src.name
    util.atomic_write(dst, text)
    src.unlink()
    sessions.log(session_id, "result", f"Archived {prompt_id} as {outcome}")
    sessions.end(session_id, outcome=f"Prompt {prompt_id}: {outcome}", resume_point=resume_point)
    return {"prompt_id": prompt_id, "session_id": session_id, "path": str(dst), "status": "ARCHIVED", "outcome": outcome}
