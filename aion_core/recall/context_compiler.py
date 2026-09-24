"""Read-only, deterministic derived context for bounded AI work.

Canonical AION SQLite and raw session logs remain authoritative.  This module
opens SQLite read-only and emits rebuildable projections under
``$AION_HOME/context``; it never creates operational state or calls a model.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import time
from collections import defaultdict
from pathlib import Path

from .. import config, db, security, util

DEFAULT_BUDGET_BYTES = 28 * 1024
MIN_BUDGET_BYTES = 4 * 1024
MAX_ITEM_CHARS = 900
SCHEMA_VERSION = 1

TOPIC_KEYWORDS = {
    "architecture": ("architecture", "authority", "canonical", "control plane", "schema"),
    "ui-ux": ("ui", "ux", "interface", "visual", "theme", "design"),
    "infrastructure": ("infrastructure", "service unit", "host adapter", "gateway", "node", "ssh", "network"),
    "security-privacy": ("security", "privacy", "secret", "credential", "permission", "encryption"),
    "context-memory": ("context", "memory", "session", "summary", "token", "checkpoint", "resume"),
    "automation": ("automation", "autonomous", "supervisor", "worker", "scheduler", "timer"),
    "deployment": ("deploy", "deployment", "release", "merge", "production", "rollback"),
    "testing": ("test", "verify", "validation", "regression", "ci", "gate"),
    "mobile-owner-console": ("mobile", "iphone", "whatsapp", "telegram", "owner console"),
    "lucynest": ("lucynest", "lucy-nest", "touchscreen", "nebula"),
    "mark-2": ("mark-2", "mark2", "droplet"),
    "lucy-den": ("lucy-den", "scs.admin01", "local node"),
    "learnrepo": ("learnrepo", "talent hunter", "candidate repo"),
    "business": ("business", "revenue", "client", "finance", "sales"),
}
ACTIVE = {"INBOX", "TRIAGE", "READY", "CLAIMED", "RUNNING", "WAITING", "BLOCKED",
          "NEEDS_REVIEW", "NEEDS_APPROVAL", "FAILED"}


class ContextCompilerError(RuntimeError):
    pass


def _clean(value, metrics: dict) -> str:
    text = str(value or "").strip()
    findings = security.scan_text(text)
    if findings:
        metrics["rejected_sensitive_items"] += len(findings)
    return security.redact(text)


def _clip(text: str, limit: int = MAX_ITEM_CHARS) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[:limit - 1] + "…"


def _hash(value) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _ro_connection(path: Path):
    path = path.resolve()
    if not path.is_file():
        raise ContextCompilerError(f"canonical database missing: {path}")
    if path != config.db_path().resolve():
        raise ContextCompilerError("compiler may read only the configured canonical database")
    try:
        conn = db.connect()
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    except Exception as exc:
        raise ContextCompilerError(f"canonical database unreadable: {exc}") from exc
    if integrity != "ok":
        raise ContextCompilerError(f"canonical database integrity failure: {integrity}")
    required = {"tasks", "sessions", "approvals", "errors", "memory"}
    present = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    missing = sorted(required - present)
    if missing:
        raise ContextCompilerError("canonical database missing tables: " + ", ".join(missing))
    return conn


def _topics(text: str) -> list[str]:
    low = text.lower()
    tags = [topic for topic, words in TOPIC_KEYWORDS.items() if any(w in low for w in words)]
    return tags or ["other"]


def _source_item(kind: str, identity: str, project: str, title: str, body: str,
                 timestamp: str, status: str, sensitivity: str, provenance: str,
                 metrics: dict) -> dict:
    title = _clean(title, metrics)
    body = _clip(_clean(body, metrics))
    project = _clean(project or "default", metrics) or "default"
    item = {
        "id": f"{kind}:{identity}", "kind": kind, "project": project,
        "title": title, "body": body, "timestamp": timestamp or "",
        "status": status or "", "sensitivity": sensitivity or "INTERNAL",
        "topics": _topics(" ".join((project, title, body))),
        "provenance": provenance,
    }
    item["content_hash"] = _hash({k: item[k] for k in item if k != "content_hash"})
    return item


def _session_log_excerpt(path: str, metrics: dict) -> tuple[str, str]:
    p = Path(path)
    if not p.is_file():
        raise ContextCompilerError(f"session source missing: {p}")
    try:
        text = p.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ContextCompilerError(f"session source unreadable: {p}: {exc}") from exc
    significant = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) >= 3 and cells[1] in {"decision", "approval", "failure", "result", "test", "handoff"}:
            significant.append(f"{cells[1]}: {cells[2]}")
    return _clip(_clean("; ".join(significant[-6:]), metrics)), hashlib.sha256(text.encode()).hexdigest()


def _discover(repo: Path, db_path: Path, metrics: dict) -> tuple[list[dict], dict[str, str]]:
    conn = _ro_connection(db_path)
    items: list[dict] = []
    hashes: dict[str, str] = {}
    try:
        for r in conn.execute("SELECT * FROM tasks ORDER BY created_at, task_id"):
            body = "; ".join(x for x in (
                r["description"], f"Blocker: {r['blockers']}" if r["blockers"] else "",
                f"Next: {r['next_action']}" if r["next_action"] else "",
                f"Evidence: {r['evidence']}" if r["evidence"] else "") if x)
            item = _source_item("task", r["task_id"], r["project"], r["title"], body,
                                r["updated_at"], r["status"], r["data_class"],
                                f"sqlite:tasks:{r['task_id']}", metrics)
            items.append(item); hashes[item["id"]] = item["content_hash"]
        for r in conn.execute("SELECT * FROM sessions ORDER BY started_at, session_id"):
            excerpt, log_hash = _session_log_excerpt(r["log_path"], metrics)
            body = "; ".join(x for x in (
                f"Objective: {r['objective']}" if r["objective"] else "",
                f"Outcome: {r['outcome']}" if r["outcome"] else "",
                f"Resume: {r['resume_point']}" if r["resume_point"] else "",
                f"Tasks: {r['tasks_touched']}" if r["tasks_touched"] else "", excerpt) if x)
            project = "LucyOS"
            item = _source_item("session", r["session_id"], project, r["objective"] or r["session_id"],
                                body, r["ended_at"] or r["started_at"], r["status"], "INTERNAL",
                                f"sqlite:sessions:{r['session_id']}|file:{r['log_path']}", metrics)
            item["source_log_hash"] = log_hash
            items.append(item); hashes[item["id"]] = _hash((item["content_hash"], log_hash))
        for r in conn.execute("SELECT * FROM approvals ORDER BY created_at, approval_id"):
            body = "; ".join(x for x in (r["why"], r["owner_action"], r["prepared"], r["resumes"]) if x)
            item = _source_item("approval", r["approval_id"], r["project"], r["action"], body,
                                r["decided_at"] or r["created_at"], r["status"], "CONFIDENTIAL",
                                f"sqlite:approvals:{r['approval_id']}", metrics)
            items.append(item); hashes[item["id"]] = item["content_hash"]
        for r in conn.execute("SELECT * FROM errors ORDER BY created_at, error_id"):
            body = "; ".join(x for x in (r["message"], r["root_cause"], r["fix"], r["lesson"]) if x)
            item = _source_item("error", r["error_id"], r["component"], r["kind"], body,
                                r["resolved_at"] or r["created_at"], r["status"], "INTERNAL",
                                f"sqlite:errors:{r['error_id']}", metrics)
            items.append(item); hashes[item["id"]] = item["content_hash"]
        for r in conn.execute("SELECT * FROM memory ORDER BY at, memory_id"):
            item = _source_item("memory", r["memory_id"], r["project"], r["title"], r["body"],
                                r["source_date"] or r["at"], r["kind"], "INTERNAL",
                                f"sqlite:memory:{r['memory_id']}|source:{r['source']}", metrics)
            items.append(item); hashes[item["id"]] = item["content_hash"]
    finally:
        pass
    def git(*args: str) -> str:
        p = subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=False)
        return p.stdout.strip() if p.returncode == 0 else ""
    head, branch = git("rev-parse", "HEAD"), git("branch", "--show-current")
    dirty = git("status", "--short")
    item = _source_item("repository", head or "unknown", "LucyOS", "Repository state",
                        f"branch={branch or 'detached'}; head={head or 'unknown'}; dirty={bool(dirty)}",
                        "", "DIRTY" if dirty else "CLEAN", "INTERNAL", "git:HEAD+status", metrics)
    items.append(item); hashes[item["id"]] = item["content_hash"]
    metrics["source_count"] = len(items)
    return items, hashes


def _score(item: dict, task: dict | None, project: str | None, newest: str) -> int:
    score = 0
    if task and (item["id"] == f"task:{task['task_id']}" or task["task_id"] in item["body"]): score += 100
    target_project = project or (task or {}).get("project")
    if target_project and item["project"].lower() == target_project.lower(): score += 35
    if item["status"] in ACTIVE or item["status"] == "PENDING": score += 30
    if item["kind"] == "approval" and item["status"] == "PENDING": score += 45
    if item["kind"] in {"task", "error", "repository"}: score += 15
    if item["timestamp"] and newest and item["timestamp"] >= newest: score += 10
    if task:
        wanted = set(_topics(" ".join((task.get("title", ""), task.get("description", "")))))
        score += 8 * len(wanted & set(item["topics"]))
    return score


def _deduplicate(items: list[dict], task: dict | None, project: str | None) -> list[dict]:
    newest = sorted((x["timestamp"] for x in items if x["timestamp"]), reverse=True)
    cutoff = newest[min(9, len(newest) - 1)] if newest else ""
    best: dict[str, dict] = {}
    for item in items:
        item = dict(item)
        item["score"] = _score(item, task, project, cutoff)
        key = _hash((item["project"].lower(), item["title"].lower(), item["body"].lower()))
        if key not in best or (item["score"], item["timestamp"], item["id"]) > (
                best[key]["score"], best[key]["timestamp"], best[key]["id"]):
            best[key] = item
    return sorted(best.values(), key=lambda x: (-x["score"], x["kind"], x["id"]))


def _task_dict(items: list[dict], task_id: str | None) -> dict | None:
    if not task_id: return None
    for item in items:
        if item["id"] == f"task:{task_id}":
            return {"task_id": task_id, "project": item["project"], "title": item["title"],
                    "description": item["body"], "status": item["status"],
                    "provenance": item["provenance"]}
    raise ContextCompilerError(f"no such canonical task: {task_id}")


def _render_markdown(packet: dict) -> str:
    lines = ["# CURRENT CONTEXT", "", "_Derived, read-only and rebuildable; canonical AION evidence wins._", "",
             f"Source revision: `{packet['source_revision']}`", f"Task: `{packet.get('task_id') or 'none'}`",
             f"Project: `{packet.get('project') or 'all'}`", "", "## Active owner gates"]
    gates = packet["owner_gates"]
    lines += [f"- **{x['title']}** — {x['body']} ({x['provenance']})" for x in gates] or ["- none"]
    lines += ["", "## Current blockers"]
    blockers = packet["blockers"]
    lines += [f"- **{x['title']}** — {x['body']} ({x['provenance']})" for x in blockers] or ["- none"]
    lines += ["", "## Selected evidence"]
    for x in packet["selected"]:
        lines += [f"### {x['title']}",
                  f"- Kind/status: {x['kind']} / {x['status'] or 'n/a'}",
                  f"- Project/topics: {x['project']} / {', '.join(x['topics'])}",
                  f"- Evidence: {x['body'] or 'no detail recorded'}",
                  f"- Provenance: `{x['provenance']}`", ""]
    lines += ["## Execution contract", "",
              "UNDERSTAND → INSPECT LIVE REALITY → REPRODUCE / MEASURE → FIND ROOT CAUSE → DESIGN SMALLEST SAFE CHANGE → IMPLEMENT → TEST → REVIEW → ARCHITECTURE / SECURITY CHECK → RECORD EVIDENCE → CHECK FOR LOOP / DUPLICATION → ADVANCE OR BLOCK",
              "", "Maximum three attempts on one root failure. Never mark DONE without evidence.", ""]
    return "\n".join(lines)


def _packet(items: list[dict], task: dict | None, project: str | None,
            revision: str, budget: int, metrics: dict) -> tuple[dict, str, str]:
    target_project = project or (task or {}).get("project")
    eligible = [x for x in items if not target_project
                or x["project"].lower() == target_project.lower()
                or x["kind"] == "repository"]
    ranked = _deduplicate(eligible, task, target_project)
    gates = [x for x in ranked if x["kind"] == "approval" and x["status"] == "PENDING"]
    blockers = [x for x in ranked if x["status"] in {"BLOCKED", "FAILED"}]
    chosen: list[dict] = []
    base = {"schema_version": SCHEMA_VERSION, "source_revision": revision,
            "task_id": task["task_id"] if task else None,
            "project": target_project,
            "owner_gates": gates, "blockers": blockers, "selected": chosen,
            "metrics": {"source_count": metrics["source_count"],
                        "rejected_sensitive_items": metrics["rejected_sensitive_items"]}}
    for item in ranked:
        trial = dict(base, selected=chosen + [item])
        md = _render_markdown(trial)
        js = json.dumps(trial, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
        if len(md.encode()) <= budget and len(js.encode()) <= budget:
            chosen.append(item)
    packet = dict(base, selected=chosen)
    packet["metrics"]["selected_count"] = len(chosen)
    md = _render_markdown(packet)
    js = json.dumps(packet, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    if len(md.encode()) > budget or len(js.encode()) > budget:
        raise ContextCompilerError("mandatory context exceeds configured budget")
    security.assert_clean(md, "CURRENT_CONTEXT.md")
    security.assert_clean(js, "CURRENT_CONTEXT.json")
    return packet, md, js


def _write_if_changed(path: Path, text: str) -> bool:
    if path.is_file() and path.read_text(encoding="utf-8") == text:
        return False
    util.atomic_write(path, text)
    return True


def _write_projections(root: Path, items: list[dict]) -> int:
    changed = 0
    for item in items:
        if item["kind"] != "session": continue
        text = "\n".join((f"# {item['id']}", "", "_Derived session summary._", "",
                           f"- Timestamp: {item['timestamp'] or 'not recorded'}",
                           f"- Project: {item['project']}", f"- Status: {item['status']}",
                           f"- Topics: {', '.join(item['topics'])}", f"- Source: `{item['provenance']}`",
                           "", item["body"] or "No material summary recorded.", ""))
        security.assert_clean(text, item["id"])
        changed += _write_if_changed(root / "sessions" / "summaries" / f"{item['id'].split(':',1)[1]}.md", text)
    projects: dict[str, list[dict]] = defaultdict(list)
    topics: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        projects[item["project"]].append(item)
        for topic in item["topics"]: topics[topic].append(item)
    for project, rows in sorted(projects.items()):
        slug = re.sub(r"[^a-z0-9]+", "-", project.lower()).strip("-") or "default"
        active = [x for x in rows if x["kind"] == "task" and x["status"] in ACTIVE]
        gates = [x for x in rows if x["kind"] == "approval" and x["status"] == "PENDING"]
        blockers = [x for x in rows if x["status"] in {"BLOCKED", "FAILED"}]
        decisions = [x for x in rows if x["kind"] == "memory" and x["status"] == "decision"]
        repositories = [x for x in rows if x["kind"] == "repository"]
        latest = sorted(rows, key=lambda x: (x["timestamp"], x["id"]), reverse=True)[:12]
        lines = [f"# {project} Project Summary", "", "_Derived view; canonical AION remains authoritative._", "",
                 "## Active work"]
        lines += [f"- {x['title']} [{x['status']}] — {x['body']} (`{x['provenance']}`)" for x in active] or ["- none"]
        lines += ["", "## Owner gates"]
        lines += [f"- {x['title']} — {x['body']} (`{x['provenance']}`)" for x in gates] or ["- none"]
        lines += ["", "## Blockers"]
        lines += [f"- {x['title']} — {x['body']} (`{x['provenance']}`)" for x in blockers] or ["- none"]
        lines += ["", "## Decisions"]
        lines += [f"- {x['title']} — {x['body']} (`{x['provenance']}`)" for x in decisions[-12:]] or ["- none"]
        lines += ["", "## Repository state"]
        lines += [f"- {x['body']} (`{x['provenance']}`)" for x in repositories] or ["- not available"]
        lines += ["", "## Recent evidence"]
        lines += [f"- {x['title']} — {x['body']} (`{x['provenance']}`)" for x in latest]
        text = "\n".join(lines) + "\n"
        security.assert_clean(text, f"project:{project}")
        changed += _write_if_changed(root / "projects" / slug / "PROJECT_SUMMARY.md", text)
    for topic in sorted(set(TOPIC_KEYWORDS) | set(topics)):
        rows = topics.get(topic, [])
        latest = sorted(rows, key=lambda x: (x["timestamp"], x["id"]), reverse=True)[:20]
        lines = [f"# Topic: {topic}", "", "_Derived projection; follow provenance to source evidence._", ""]
        lines += ([f"- [{x['project']}] {x['title']} [{x['status'] or x['kind']}] — {x['body']} (`{x['provenance']}`)" for x in latest]
                  or ["- no matching local evidence"])
        text = "\n".join(lines) + "\n"
        security.assert_clean(text, f"topic:{topic}")
        changed += _write_if_changed(root / "topics" / f"{topic}.md", text)
    return changed


def compile_context(*, repo: Path, task_id: str | None = None, project: str | None = None,
                    output_root: Path | None = None, budget_bytes: int = DEFAULT_BUDGET_BYTES,
                    db_path: Path | None = None) -> dict:
    """Compile derived context without mutating canonical AION state."""
    started = time.monotonic()
    if budget_bytes < MIN_BUDGET_BYTES:
        raise ContextCompilerError(f"budget must be at least {MIN_BUDGET_BYTES} bytes")
    repo = Path(repo).resolve()
    root = Path(output_root or (config.home() / "context")).resolve()
    db_path = Path(db_path or config.db_path())
    metrics = {"source_count": 0, "rejected_sensitive_items": 0}
    items, source_hashes = _discover(repo, db_path, metrics)
    task = _task_dict(items, task_id)
    revision = _hash(source_hashes)
    compiler_hash = util.sha256_file(Path(__file__))
    build_key = _hash({"revision": revision, "task": task_id, "project": project,
                       "budget": budget_bytes, "schema": SCHEMA_VERSION,
                       "compiler_hash": compiler_hash})
    manifest_path = root / "current" / "MANIFEST.json"
    old = util.read_json(manifest_path, {}) or {}
    current_md = root / "current" / "CURRENT_CONTEXT.md"
    current_json = root / "current" / "CURRENT_CONTEXT.json"
    unchanged = old.get("build_key") == build_key and current_md.is_file() and current_json.is_file()
    hits = sum(1 for key, value in source_hashes.items() if old.get("source_hashes", {}).get(key) == value)
    misses = len(source_hashes) - hits
    if unchanged:
        for p in (current_md, current_json):
            security.assert_clean(p.read_text(encoding="utf-8"), str(p))
            if p.stat().st_size > budget_bytes:
                raise ContextCompilerError(f"cached output exceeds budget: {p}")
        return {"status": "CACHE_HIT", "task_id": task_id, "project": project,
                "source_count": len(source_hashes), "selected_count": old.get("selected_count", 0),
                "output": {"markdown": str(current_md), "json": str(current_json)},
                "bytes": {"markdown": current_md.stat().st_size, "json": current_json.stat().st_size},
                "cache": {"hits": len(source_hashes), "misses": 0},
                "rejected_sensitive_items": old.get("rejected_sensitive_items", 0),
                "build_duration_ms": round((time.monotonic() - started) * 1000, 3),
                "source_revision": revision}
    packet, md, js = _packet(items, task, project, revision, budget_bytes, metrics)
    projection_changes = _write_projections(root, items)
    _write_if_changed(current_md, md)
    _write_if_changed(current_json, js)
    manifest = {"schema_version": SCHEMA_VERSION, "build_key": build_key,
                "compiler_hash": compiler_hash,
                "source_revision": revision, "source_hashes": source_hashes,
                "source_count": len(source_hashes), "selected_count": len(packet["selected"]),
                "budget_bytes": budget_bytes, "output_bytes": {"markdown": len(md.encode()), "json": len(js.encode())},
                "output_hashes": {"markdown": hashlib.sha256(md.encode()).hexdigest(),
                                  "json": hashlib.sha256(js.encode()).hexdigest()},
                "cache": {"hits": hits, "misses": misses},
                "projection_files_changed": projection_changes,
                "rejected_sensitive_items": metrics["rejected_sensitive_items"],
                "build_duration_ms": round((time.monotonic() - started) * 1000, 3)}
    util.write_json(manifest_path, manifest)
    return {"status": "BUILT", "task_id": task_id, "project": project,
            "source_count": len(source_hashes), "selected_count": len(packet["selected"]),
            "output": {"markdown": str(current_md), "json": str(current_json)},
            "bytes": manifest["output_bytes"], "cache": manifest["cache"],
            "rejected_sensitive_items": metrics["rejected_sensitive_items"],
            "build_duration_ms": manifest["build_duration_ms"], "source_revision": revision}
