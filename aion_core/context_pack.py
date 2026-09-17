"""Deterministic compact repo/runtime context for high-token planners.

No model calls. Produces a bounded delta packet so planners can review changes
instead of re-reading the repository on every turn.
"""
from __future__ import annotations

import hashlib, json, subprocess
from pathlib import Path

from . import config, db, health, resume, security, skills, util

MAX_MARKDOWN_BYTES = 30 * 1024
DEFAULT_RELEVANT = [
    "docs/LUCYOS_OPENCLAW_INTEGRATION_EXECUTION_PLAN.md",
    "integrations/openclaw/lucyos/SKILL.md",
    "integrations/openclaw/lucyos/scripts/lucyosctl",
    "tests/test_openclaw_lucyos_bridge.py",
    "aion_core/context.py", "aion_core/resume.py", "aion_core/router.py",
    "aion_core/architecture.py",
]

def _git(repo: Path, *args: str) -> str:
    p = subprocess.run(["git", *args], cwd=repo, text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    return p.stdout.strip() if p.returncode == 0 else ""

def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def _changed(repo: Path, watermark: str, head: str) -> list[str]:
    if not watermark or not head:
        return []
    if subprocess.run(["git", "cat-file", "-e", f"{watermark}^{{commit}}"], cwd=repo,
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
        return []
    text = _git(repo, "diff", "--name-only", f"{watermark}..{head}")
    return [x for x in text.splitlines() if x][:200]

def build(repo: Path, *, focus: str = "", watermark: str | None = None,
          output_dir: Path | None = None) -> dict:
    repo = repo.resolve()
    head = _git(repo, "rev-parse", "HEAD")
    branch = _git(repo, "branch", "--show-current")
    watermark = watermark or db.get_meta("last_high_model_reviewed_commit", "")
    changed = _changed(repo, watermark, head)
    dirty = [x for x in _git(repo, "status", "--short").splitlines() if x][:100]
    r = resume.load()
    h = health.run_all(deep=False)
    rows = skills.all_skills()
    enabled = [x["skill_id"] for x in rows if x["enabled"]]
    relevant = []
    for rel in DEFAULT_RELEVANT + changed:
        if rel not in relevant and (repo / rel).is_file():
            relevant.append(rel)
    files = [{"path": rel, "sha256": _sha(repo / rel), "bytes": (repo / rel).stat().st_size}
             for rel in relevant[:30]]
    packet = {
        "schema_version": 1, "generated_at": util.now(), "focus": focus,
        "repo": str(repo), "branch": branch, "head": head,
        "review_watermark": watermark or None, "changed_files": changed,
        "dirty_status": dirty, "resume": {k: r.get(k) for k in (
            "objective", "current_state", "current_task", "last_verified_success",
            "last_failure", "bottleneck", "next_action", "files_to_read")},
        "health": {"healthy": h["healthy"], "failing": h["failing"]},
        "skills": {"registered": len(rows), "enabled": enabled},
        "recommended_files": files,
        "planner_rule": "Cross-check this packet and inspect only changed/recommended files unless evidence conflicts.",
    }
    out = output_dir or (config.home() / "context" / "current")
    out.mkdir(parents=True, exist_ok=True)
    (out / "context.json").write_text(json.dumps(packet, indent=2, sort_keys=True), encoding="utf-8")
    md = render_markdown(packet)
    if len(md.encode()) > MAX_MARKDOWN_BYTES:
        md = md.encode()[:MAX_MARKDOWN_BYTES].decode("utf-8", "ignore") + "\n\n[TRUNCATED AT 30 KiB]\n"
    (out / "context.md").write_text(security.redact(md), encoding="utf-8")
    return {"output": str(out), "bytes": len(md.encode()), "packet": packet}

def render_markdown(p: dict) -> str:
    lines = ["# LucyOS AI Context Packet", "",
        f"Generated: {p['generated_at']}", f"Focus: {p['focus'] or 'not specified'}",
        f"Branch: {p['branch']}", f"HEAD: {p['head']}",
        f"Last high-model reviewed commit: {p['review_watermark'] or 'none'}", "",
        "## Runtime", f"Health: {'healthy' if p['health']['healthy'] else 'DEGRADED'}",
        f"Failing: {', '.join(p['health']['failing']) or 'none'}",
        f"Enabled skills: {', '.join(p['skills']['enabled']) or 'none'}", "",
        "## Resume state"]
    for k,v in p["resume"].items(): lines.append(f"- {k}: {v or 'not set'}")
    lines += ["", "## Delta since last high-model review"]
    lines += [f"- {x}" for x in p["changed_files"]] or ["- no committed delta or no watermark"]
    lines += ["", "## Working tree"]
    lines += [f"- {x}" for x in p["dirty_status"]] or ["- clean"]
    lines += ["", "## Read these first"]
    lines += [f"- {x['path']} ({x['bytes']} B, sha256 {x['sha256'][:12]}...)" for x in p["recommended_files"]]
    lines += ["", "## Planner instruction",
        "Treat this packet as a deterministic index, not unquestionable truth.",
        "Cross-check claims against the listed changed/recommended files and live runtime evidence.",
        "Do not rescan the full repository unless the packet is missing, inconsistent, or a required file is not indexed."]
    return "\n".join(lines) + "\n"

def mark_reviewed(repo: Path, commit: str | None = None) -> str:
    commit = commit or _git(repo.resolve(), "rev-parse", "HEAD")
    if not commit: raise ValueError("cannot resolve reviewed commit")
    db.set_meta("last_high_model_reviewed_commit", commit)
    return commit
