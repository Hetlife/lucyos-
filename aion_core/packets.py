"""AI SYNC PACKET ingestion.

An external ChatGPT/Claude/Fable session cannot write to the shared brain
directly.  It emits a packet in the directive's format; this module parses it,
deduplicates it, flags conflicts with existing local state instead of silently
overwriting, and turns its TASKS / APPROVALS sections into real rows.
"""
from __future__ import annotations

import re
from pathlib import Path

from . import approvals, config, db, memory, security, tasks, util

HEADER_RE = re.compile(r"^([A-Z_]+):\s*(.*)$")
SECTION_RE = re.compile(r"^##\s+(.+?)\s*$")

REQUIRED_HEADERS = ("SOURCE",)


class PacketError(Exception):
    pass


def parse(text: str) -> dict:
    """Parse the packet text into headers + sections.  Tolerant of minor drift."""
    headers: dict[str, str] = {}
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.strip().upper().startswith("# AI SYNC PACKET"):
            continue
        if line.strip().upper() == "END AI SYNC PACKET":
            break
        m = SECTION_RE.match(line)
        if m:
            current = m.group(1).strip().upper()
            sections.setdefault(current, [])
            continue
        if current is None:
            hm = HEADER_RE.match(line.strip())
            if hm:
                headers[hm.group(1).upper()] = hm.group(2).strip()
            continue
        sections[current].append(line)
    body = {k: "\n".join(v).strip() for k, v in sections.items()}
    missing = [h for h in REQUIRED_HEADERS if not headers.get(h)]
    if missing:
        raise PacketError(f"packet missing required header(s): {', '.join(missing)}")
    return {"headers": headers, "sections": body}


def _lines(section: str) -> list[str]:
    out = []
    for line in (section or "").splitlines():
        line = line.strip().lstrip("-*").strip()
        if line:
            out.append(line)
    return out


def ingest(text: str, *, source_path: Path | None = None, actor: str = "sync") -> dict:
    """Ingest one packet.  Idempotent by PACKET_ID and by content hash."""
    findings = security.scan_text(text)
    if findings:
        # A packet must never carry credentials into the shared brain.
        text = security.redact(text)
    parsed = parse(text)
    headers = parsed["headers"]
    sections = parsed["sections"]
    # Hash the content, not the envelope: the same work re-emitted under a new
    # PACKET_ID is still the same work and must not be applied twice.
    canonical = "\n".join(
        line for line in text.strip().splitlines()
        if not line.strip().upper().startswith(("PACKET_ID:", "TIMESTAMP:", "SOURCE_SESSION:"))
    ).strip()
    digest = util.sha256_text(canonical)
    packet_id = headers.get("PACKET_ID") or f"PKT-{digest[:10].upper()}"

    conn = db.connect()
    existing = conn.execute(
        "SELECT packet_id, status FROM packets WHERE packet_id=? OR hash=?",
        (packet_id, digest)).fetchone()
    if existing:
        return {"packet_id": existing["packet_id"], "status": "DUPLICATE",
                "duplicate_of": existing["packet_id"], "tasks": [], "approvals": [],
                "conflicts": [], "redacted": bool(findings)}

    stored = None
    if source_path is not None:
        stored = str(source_path)
    conn.execute(
        "INSERT INTO packets(packet_id, source, source_session, received_at, timestamp, project, "
        "topic, hash, status, stored_path) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (packet_id, headers.get("SOURCE", "unknown"), headers.get("SOURCE_SESSION"),
         util.now(), headers.get("TIMESTAMP"), headers.get("PROJECT", "default"),
         headers.get("TOPIC", ""), digest, "PROCESSING", stored))
    conn.commit()

    result = {"packet_id": packet_id, "status": "PROCESSED", "tasks": [], "approvals": [],
              "facts": 0, "conflicts": [], "redacted": bool(findings)}
    try:
        project = headers.get("PROJECT", "default")
        result["conflicts"] = _detect_conflicts(sections)
        result["facts"] = _ingest_memory(sections, project, packet_id)
        result["tasks"] = _ingest_tasks(sections, project, packet_id)
        result["approvals"] = _ingest_approvals(sections, project)
        _ingest_resume(sections, packet_id)
        conn.execute("UPDATE packets SET status='PROCESSED', processed_at=? WHERE packet_id=?",
                     (util.now(), packet_id))
        conn.commit()
        db.log_event(actor, "packet.ingest", packet_id,
                     f"{len(result['tasks'])} tasks, {len(result['approvals'])} approvals")
    except Exception as exc:  # keep the packet, mark it failed, never lose it
        conn.execute("UPDATE packets SET status='FAILED', error=? WHERE packet_id=?",
                     (str(exc)[:500], packet_id))
        conn.commit()
        from . import errors
        errors.record("packets", f"packet {packet_id} failed: {exc}")
        result["status"] = "FAILED"
        result["error"] = str(exc)
    return result


def _ingest_memory(sections: dict, project: str, packet_id: str) -> int:
    count = 0
    mapping = [
        ("VERIFIED FACTS", "fact", "VERIFIED_FACT"),
        ("INFERENCES / ASSUMPTIONS", "fact", "ASSUMPTION"),
        ("DECISIONS", "decision", "SUPPORTED_FACT"),
        ("RESEARCH FINDINGS", "research", "SUPPORTED_FACT"),
        ("RISKS", "fact", "INFERENCE"),
    ]
    for name, kind, confidence in mapping:
        for line in _lines(sections.get(name, "")):
            memory.remember(kind, line[:120], line, project=project, confidence=confidence,
                            source=packet_id)
            count += 1
    return count


def _ingest_tasks(sections: dict, project: str, packet_id: str) -> list[str]:
    """TASKS CREATED lines: 'TITLE | PRIORITY | DEPENDENCIES | SUCCESS CRITERIA'."""
    created = []
    for line in _lines(sections.get("TASKS CREATED", "")):
        parts = [p.strip() for p in line.split("|")]
        title = parts[0]
        if not title:
            continue
        key = util.sha256_text(f"{project}|{title}")
        if db.seen(f"task:{key}", "packet_task", packet_id):
            continue  # duplicate prevention across repeated packets
        priority = 3
        if len(parts) > 1 and parts[1]:
            m = re.search(r"\d", parts[1])
            if m:
                priority = int(m.group(0))
        deps = parts[2] if len(parts) > 2 else ""
        criteria = parts[3] if len(parts) > 3 else ""
        created.append(tasks.create(
            title, project=project, priority=priority,
            dependencies="" if deps.lower() in ("none", "-", "") else deps,
            success_criteria=criteria, status="TRIAGE",
            description=f"From sync packet {packet_id}"))
    for line in _lines(sections.get("TASKS COMPLETED", "")):
        memory.remember("fact", f"completed: {line[:100]}", line, project=project,
                        confidence="SUPPORTED_FACT", source=packet_id)
    return created


def _ingest_approvals(sections: dict, project: str) -> list[str]:
    made = []
    for line in _lines(sections.get("APPROVALS REQUIRED", "")):
        if line.lower() in ("none", "n/a", "-"):
            continue
        unstated = "not stated by the source packet — establish before deciding"
        made.append(approvals.create(
            line, project=project,
            why="requested by an external AI session; it did not justify the cost",
            owner_action=line, cost=unstated, max_downside=unstated,
            expected_benefit=unstated, reversibility="unknown",
            prepared="nothing — this arrived as a request, not as prepared work",
            resumes="establish cost, downside and reversibility, then re-ask",
            recommendation="REVIEW — do not approve until the blanks above are filled"))
    return made


def _ingest_resume(sections: dict, packet_id: str) -> None:
    resume_point = sections.get("EXACT RESUME POINT", "").strip()
    next_actions = sections.get("NEXT HIGHEST-VALUE ACTIONS", "").strip()
    if resume_point:
        db.set_meta("packet_resume_point", resume_point[:2000])
        db.set_meta("packet_resume_source", packet_id)
    if next_actions:
        db.set_meta("packet_next_actions", next_actions[:2000])


def _detect_conflicts(sections: dict) -> list[str]:
    """Flag, never silently overwrite, facts that contradict local memory."""
    conflicts = []
    for line in _lines(sections.get("VERIFIED FACTS", "")):
        subject = line.split(":")[0].strip()
        if len(subject) < 4 or subject == line.strip():
            continue
        for row in memory.search(subject, limit=3, kind="fact"):
            if row["body"].strip() != line.strip() and row["body"].lower().startswith(subject.lower()):
                conflicts.append(f"packet says '{line}' but {row['memory_id']} says '{row['body']}'")
    return conflicts


def is_packet_file(path: Path) -> bool:
    """The folder's own documentation and dotfiles are not packets."""
    return path.is_file() and path.name != "README.md" and not path.name.startswith(".")


def pending_files() -> list[Path]:
    d = config.home() / "INBOX" / "pending"
    return [p for p in sorted(d.glob("*")) if is_packet_file(p)] if d.is_dir() else []


def ingest_inbox() -> list[dict]:
    """Process every file in INBOX/pending, moving it to processed/ or failed/."""
    root = config.home()
    pending = root / "INBOX" / "pending"
    processed = root / "INBOX" / "processed"
    failed = root / "INBOX" / "failed"
    for d in (pending, processed, failed):
        d.mkdir(parents=True, exist_ok=True)
    results = []
    for path in pending_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError) as exc:
            path.rename(failed / path.name)
            results.append({"packet_id": path.name, "status": "FAILED", "error": str(exc)})
            continue
        try:
            res = ingest(text, source_path=path)
        except PacketError as exc:
            path.rename(failed / path.name)
            from . import errors
            errors.record("packets", f"unparseable packet {path.name}: {exc}")
            results.append({"packet_id": path.name, "status": "FAILED", "error": str(exc)})
            continue
        dest = processed if res["status"] in ("PROCESSED", "DUPLICATE") else failed
        path.rename(dest / path.name)
        results.append(res)
    return results


def stats() -> dict:
    rows = db.connect().execute(
        "SELECT status, COUNT(*) c FROM packets GROUP BY status").fetchall()
    return {r["status"]: r["c"] for r in rows}
