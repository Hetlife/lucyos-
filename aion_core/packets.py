"""AI SYNC PACKET ingestion.

An external ChatGPT/Claude/Fable session cannot write to the shared brain
directly.  It emits a packet in the directive's format; this module parses it,
deduplicates it, flags conflicts with existing local state instead of silently
overwriting, and turns its TASKS / APPROVALS sections into real rows.
"""
from __future__ import annotations

import json
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

# Lucy Envelope is a side-effect-free typed handoff.  The older AI SYNC PACKET
# importer above remains unchanged; validation NEVER creates tasks or approvals.
AGENT_ENVELOPE_SCHEMA = (Path(__file__).resolve().parents[1] /
                         "docs/agent-harness/schemas/agent-message.schema.json")
ENVELOPE_STATES = {
    "REQUEST": {"QUEUED"},
    "RESULT": {"VERIFYING", "PASS", "FAIL"},
    "BLOCKER": {"BLOCKED", "ESCALATED"},
    "REVIEW": {"VERIFYING", "FAIL", "BLOCKED"},
    "APPROVAL_REQUIRED": {"BLOCKED", "ESCALATED"},
    "HEARTBEAT": {"CLAIMED", "RUNNING"},
}


def validate_agent_envelope(payload: dict, *, allowed_paths=(),
                            trusted_verifier: bool = False) -> dict:
    """Validate schema + boundaries. Never execute or authorize transitions.

    PASS is reserved for an internally verified result, not an LLM assertion.
    Caller MUST also check the live AION lease, approvals and canonical task
    transition before acting on the returned untrusted data.
    """
    if not isinstance(payload, dict):
        raise PacketError("Lucy Envelope must be an object")
    try:
        from jsonschema import Draft202012Validator, FormatChecker
    except ImportError:
        raise PacketError("jsonschema is required; refusing unvalidated envelope") from None
    schema = json.loads(AGENT_ENVELOPE_SCHEMA.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    first = next(validator.iter_errors(payload), None)
    if first is not None:
        raise PacketError("invalid Lucy Envelope: " + first.message[:180])
    from datetime import datetime
    try:
        stamped = datetime.fromisoformat(payload["created_at"].replace("Z", "+00:00"))
        if stamped.tzinfo is None or stamped.utcoffset() is None:
            raise ValueError("timezone required")
    except ValueError:
        raise PacketError("created_at must be timezone-qualified ISO 8601") from None
    if payload["status"] not in ENVELOPE_STATES[payload["type"]]:
        raise PacketError("message type/status conflict")
    if payload["status"] == "PASS" and not trusted_verifier:
        raise PacketError("worker cannot self-attest PASS")
    if payload["type"] == "RESULT" and payload["status"] == "VERIFYING" and not payload["tests"]:
        raise PacketError("RESULT must include test records")
    if payload["retry_class"] == "NEW_HYPOTHESIS" and not payload["evidence_refs"]:
        raise PacketError("new retry hypothesis requires evidence")
    for path in payload["changed_paths"]:
        p = Path(path)
        if (p.is_absolute() or ".." in p.parts or chr(92) in path
                or not any(path == scope or (scope.endswith("/") and path.startswith(scope))
                           for scope in allowed_paths)):
            raise PacketError("changed path outside explicitly granted scope")
    for check in payload["tests"]:
        if check["status"] == "PASS" and not check.get("evidence_ref"):
            raise PacketError("test PASS requires evidence pointer")
    if security.scan_text(json.dumps(payload, sort_keys=True, ensure_ascii=False)):
        raise PacketError("Lucy Envelope contains secret-shaped content")
    return dict(payload)


def propose_agent_collaboration(parent_task_id: str, assignments: list[dict]) -> dict:
    """Read-only collaboration plan from existing child tasks and agent registry.

    The proposed workers still require an actual AION claim and authorization.
    No concurrent mutable resource may be assigned twice, even to distinct tasks.
    """
    from . import agents
    parent = tasks.get(parent_task_id)
    if parent is None:
        raise PacketError("unknown canonical parent task")
    if not isinstance(assignments, list) or not 1 <= len(assignments) <= 12:
        raise PacketError("invalid collaboration size")
    roles = {"builder", "reviewer", "verifier", "researcher"}
    proposed = []
    used_tasks = set()
    mutable = []
    for assignment in assignments:
        if not isinstance(assignment, dict) or set(assignment) != {
                "task_id", "agent_id", "role", "capability", "writable_paths"}:
            raise PacketError("invalid collaboration assignment")
        task_id, agent_id = assignment["task_id"], assignment["agent_id"]
        role, capability = assignment["role"], assignment["capability"]
        if not isinstance(task_id, str) or task_id in used_tasks:
            raise PacketError("duplicate or invalid child task")
        used_tasks.add(task_id)
        child = tasks.get(task_id)
        if child is None or child["parent_task"] != parent_task_id or child["project"] != parent["project"]:
            raise PacketError("child must link to the existing parent/project in AION")
        if child["status"] in {"DONE", "CANCELLED", "FAILED"}:
            raise PacketError("cannot assign closed child task")
        agent = agents.get(agent_id) if isinstance(agent_id, str) else None
        if agent is None or not agent["enabled"]:
            raise PacketError("agent must be registered and enabled")
        if not isinstance(role, str) or role not in roles:
            raise PacketError("unsupported collaboration role")
        if not isinstance(capability, str) or not capability or len(capability) > 64:
            raise PacketError("requested capability must be a bounded string")
        capabilities = set(str(agent["capabilities"] or "").split(","))
        if capability not in capabilities:
            raise PacketError("registered agent lacks requested capability")
        paths = assignment["writable_paths"]
        if not isinstance(paths, list) or len(paths) > 12 or role in {"reviewer", "researcher", "verifier"} and paths:
            raise PacketError("read-only reviewer/researcher/verifier cannot mutate resources")
        norm = []
        for path in paths:
            if (not isinstance(path, str) or not path or len(path) > 180
                    or path.startswith(".") or chr(92) in path):
                raise PacketError("invalid writable resource scope")
            p = Path(path)
            if p.is_absolute() or ".." in p.parts or "//" in path:
                raise PacketError("unsafe writable resource scope")
            # Read the frozen authority contract instead of duplicating a
            # protected-file list; fail closed if it cannot be loaded.
            from fnmatch import fnmatchcase
            authority_file = (Path(__file__).resolve().parents[1] /
                              ".lucy/authority/HIGH_MODEL_BASELINE.json")
            try:
                protected = json.loads(authority_file.read_text(encoding="utf-8"))["protected_paths"]
                if not isinstance(protected, list) or not protected:
                    raise ValueError("empty policy")
            except (OSError, ValueError, KeyError, TypeError):
                raise PacketError("canonical protected-path contract unavailable") from None
            canonical_path = p.as_posix()
            if canonical_path != path.rstrip("/") or (Path(__file__).resolve().parents[1] / path).is_symlink():
                raise PacketError("noncanonical or linked mutation scope")
            if (path in {"aion_core", "docs", "tests", "scripts"}
                    or any(fnmatchcase(path, pattern)
                           or (pattern.endswith("/**") and path == pattern[:-3])
                           for pattern in protected)):
                raise PacketError("protected or overly broad mutation scope")
            norm.append(path.rstrip("/"))
        for path in norm:
            for other in mutable:
                if path == other or path.startswith(other + "/") or other.startswith(path + "/"):
                    raise PacketError("overlapping mutation scopes require serial integration")
        mutable.extend(norm)
        proposed.append({"task_id": task_id, "agent_id": agent_id, "role": role,
                         "capability": capability, "writable_paths": paths,
                         "cost_class": agent["cost_class"], "model_class": agent["model_class"],
                         "measured_agent_runs": agent["runs"], "reliability": agent["reliability"],
                         "capability_status": "REGISTERED_NOT_LIVE_VERIFIED"})
    return {"parent_task_id": parent_task_id, "assignment_proposals": proposed,
            "authority": "AION_TASK_CLAIMS_ONLY", "authorized_mutation": False,
            "note": "Parallel read-only reviews allowed; distinct scopes still require AION claims."}


def adjudicate_agent_reviews(proposal: dict, reviews: list[dict]) -> dict:
    """Deterministic, non-authoritative dispute triage. Never vote on truth.

    Even unanimous SUPPORT cannot promote a task; independent test verifier
    and AION task state transitions remain mandatory. Disputed evidence requires
    a falsifiable test, independent specialist review or owner decision.
    """
    validate_agent_envelope(proposal)
    if proposal["type"] != "RESULT" or proposal["status"] != "VERIFYING":
        raise PacketError("dispute target must be an unverified RESULT")
    if not isinstance(reviews, list) or len(reviews) > 8:
        raise PacketError("review count outside bounds")
    positions, reviewers, ref_ids = [], set(), []
    for review in reviews:
        validate_agent_envelope(review)
        if review["type"] != "REVIEW" or review["status"] != "VERIFYING":
            raise PacketError("review must be unverified REVIEW envelope")
        if (review["task_id"] != proposal["task_id"]
                or review["correlation_id"] != proposal["correlation_id"]
                or review.get("baseline_ref") != proposal.get("baseline_ref")
                or review["review_target"] != proposal["message_id"]):
            raise PacketError("review references mismatched task/baseline/result")
        if review["sender"] == proposal["sender"] or review["sender"] in reviewers:
            raise PacketError("reviewer must be distinct from builder and peers")
        reviewers.add(review["sender"])
        positions.append(review["review_position"])
        ref_ids.extend(review["evidence_refs"])
    if not reviews:
        outcome = "PENDING_INDEPENDENT_REVIEW"
        action = "Request an independent, evidence-backed review."
    elif "CHALLENGE" in positions:
        outcome = "DISPUTED"
        action = "Run a discriminating deterministic test, or ask an independent specialist to examine conflicting evidence."
    elif "UNCERTAIN" in positions:
        outcome = "INCONCLUSIVE"
        action = "Retrieve bounded missing evidence; escalate if uncertainty remains."
    else:
        outcome = "AGREED_PENDING_VERIFICATION"
        action = "Run the existing AION independent acceptance verifier; do not self-mark PASS."
    return {"task_id": proposal["task_id"], "proposal_id": proposal["message_id"],
            "state": outcome, "reviewer_count": len(reviewers),
            "positions": positions, "review_evidence_refs": sorted(set(ref_ids)),
            "next_action": action, "authorized_mutation": False,
            "task_pass_granted": False, "owner_approval_granted": False}


def rank_agent_candidates(capability: str, *, min_reliability: float = 0.9,
                          min_verified_runs: int = 5) -> dict:
    """Advisory candidates from the existing registry, not a provider availability claim.

    Never treat unknown/insufficient evidence as measured reliability, even if
    a default DB reliability is 1.0. Actual dispatch must separately check
    provider reachability, budget, task/data class and canonical owner gates.
    """
    from . import agents
    if (not isinstance(capability, str) or not capability or len(capability) > 64
            or not 0 <= min_reliability <= 1
            or not 1 <= min_verified_runs <= 1000):
        raise PacketError("invalid ranking requirements")
    cost_rank = {"none": 0, "free": 0, "low": 1, "medium": 2, "high": 3, "scarce": 4}
    options = []
    for agent in agents.all_agents():
        if not agent["enabled"] or capability not in set(
                str(agent["capabilities"] or "").split(",")):
            continue
        count = int(agent["runs"] or 0)
        reliability = float(agent["reliability"] or 0.0)
        proven = count >= min_verified_runs
        eligible = proven and reliability >= min_reliability
        cost = str(agent["cost_class"] or "").lower()
        options.append({
            "agent_id": agent["agent_id"], "model_class": agent["model_class"],
            "cost_class": cost, "runs": count,
            "recorded_reliability": reliability if proven else None,
            "candidate_status": (
                "HISTORY_ELIGIBLE" if eligible else
                "INSUFFICIENT_HISTORY" if not proven else "BELOW_RELIABILITY_THRESHOLD"
            ),
            "live_provider_health": "UNKNOWN", "auto_dispatch_approved": False,
        })
    # Only demonstrated reliability ranks ahead of unknown; among proven
    # candidates, minimize reported cost and maximize demonstrated accuracy.
    options.sort(key=lambda item: (
        item["candidate_status"] != "HISTORY_ELIGIBLE",
        cost_rank.get(item["cost_class"], 5),
        -(item["recorded_reliability"] or 0),
        item["agent_id"],
    ))
    return {"capability": capability, "candidates": options,
            "live_probe_required": True, "authorized_dispatch": False,
            "reason": "AION agent history is not live availability or delegated authority."}


def record_authenticated_agent_review(proposal: dict, review: dict, *,
                                      authenticated_sender: str) -> dict:
    """Durably ACK one signed-in peer review in existing canonical AION events.

    Authentication MUST occur in the calling existing AION/OpenClaw bridge.
    This method accepts no credentials and does not assign leases, mark DONE,
    resolve disputes, or approve protected/owner-gated actions.
    """
    import hashlib
    if (not isinstance(authenticated_sender, str)
            or authenticated_sender != review.get("sender")):
        raise PacketError("review sender was not independently authenticated")
    decision = adjudicate_agent_reviews(proposal, [review])
    canonical = tasks.get(review["task_id"])
    if canonical is None or canonical["status"] == "CANCELLED":
        raise PacketError("review target is not an active/retained canonical task")
    serialized = json.dumps(review, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    identity_keys = (
        "lucy-review-msg:" + review["message_id"],
        "lucy-review-idempotency:" + review["idempotency_key"],
    )
    conn = db.connect()
    with conn:
        conn.execute("BEGIN IMMEDIATE")
        prior = [conn.execute("SELECT result FROM idempotency WHERE key=?", (k,)).fetchone()
                 for k in identity_keys]
        if any(prior):
            # Both identifiers must refer to the SAME already-committed record.
            if not all(prior) or prior[0]["result"] != prior[1]["result"]:
                raise PacketError("review replay keys disagree")
            stored_digest, sep, existing_id = prior[0]["result"].partition(":")
            if stored_digest != digest or not sep or not existing_id.isdigit():
                raise PacketError("review ID collision with changed content")
            return {"status": "DUPLICATE", "event_ref": f"events/{existing_id}",
                    "task_id": review["task_id"], "task_pass_granted": False,
                    "owner_approval_granted": False}
        # Store only a bounded audit summary and immutable pointers. Never write
        # the full potentially untrusted text or any user data into an event.
        event_detail = json.dumps({
            "id": review["message_id"], "result_id": proposal["message_id"],
            "position": review["review_position"], "digest": digest,
            "evidence_refs": review["evidence_refs"][:3],
        }, sort_keys=True, ensure_ascii=False)
        if len(event_detail.encode("utf-8")) > 1000:
            raise PacketError("review audit metadata exceeds limit")
        cursor = conn.execute(
            "INSERT INTO events(at,day,actor,kind,subject,detail) VALUES(?,?,?,?,?,?)",
            (util.now(), util.today(), authenticated_sender, "agent.peer_review",
             review["task_id"], security.redact(event_detail)))
        event_id = cursor.lastrowid
        receipt = f"{digest}:{event_id}"
        for key in identity_keys:
            conn.execute("INSERT INTO idempotency(key,at,scope,result) VALUES(?,?,?,?)",
                         (key, util.now(), "agent.peer_review", receipt))
    return {"status": "RECORDED", "event_ref": f"events/{event_id}",
            "task_id": review["task_id"], "triage": decision["state"],
            "task_pass_granted": False, "owner_approval_granted": False}
