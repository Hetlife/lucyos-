"""Capture and feedback — the two things the phone does that WhatsApp cannot.

Capture: the owner has an idea, a company or a project in mind and wants it in
the system in three seconds, from a queue, on a train, offline.

Feedback: the system proposes something and the owner reacts in one tap.  That
reaction must *change what the machine does next* — it writes a decision and
moves the task.  A comment box that changes nothing would be worse than useless,
because it would look like control.
"""
from __future__ import annotations

from . import config, db, memory, security, tasks, util

KINDS = ("idea", "company", "project", "note")

CHOICES = {
    "yes": ("approved by the owner", "READY"),
    "no": ("rejected by the owner", "CANCELLED"),
    "later": ("deferred by the owner", "WAITING"),
}


def capture(text: str, kind: str = "idea", *, source: str = "phone") -> dict:
    """Turn a few tapped words into the right kind of state.  Idempotent."""
    text = (text or "").strip()
    if not text:
        raise ValueError("nothing to capture")
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")

    findings = security.scan_text(text)
    if findings:
        # Same rule as WhatsApp: a credential never enters state from a keyboard.
        db.log_event(source, "capture.secret_refused",
                     ",".join(sorted({f["kind"] for f in findings})))
        raise security.SecretLeak(
            "That looks like a credential. Nothing was saved. "
            "Put the value in the secret store on the PC instead.")

    clean = security.redact(text)
    digest = util.sha256_text(f"{kind}|{clean.lower()}")
    if db.seen(f"capture:{digest}", "intake"):
        existing = db.connect().execute(
            "SELECT task_id, title FROM tasks WHERE title=? ORDER BY created_at DESC LIMIT 1",
            (clean[:120],)).fetchone()
        return {"status": "DUPLICATE", "kind": kind,
                "task_id": existing["task_id"] if existing else None,
                "message": "Already captured — nothing added twice."}

    title = clean.splitlines()[0][:120]
    if kind == "note":
        memory_id = memory.remember("fact", title, clean, confidence="ASSUMPTION",
                                    source=f"owner note via {source}")
        return {"status": "SAVED", "kind": kind, "memory_id": memory_id,
                "message": "Noted."}

    project = _project_key(title) if kind in ("company", "project") else "default"
    task_id = tasks.create(
        title,
        project=project,
        kind="triage",
        status="INBOX",
        description=f"Captured by the owner from {source} as a {kind}.\n\n{clean}",
        priority=2,
        human_dependence=0.5,
        success_criteria="triaged into either a real plan or a recorded decision not to pursue",
        next_action="triage: decide whether this becomes a project, and what the first test is",
    )
    if kind in ("company", "project"):
        _ensure_project_dir(project, clean)
    return {"status": "SAVED", "kind": kind, "task_id": task_id, "project": project,
            "message": f"Captured as {task_id}. It will be triaged, not forgotten."}


def _project_key(title: str) -> str:
    """A stable, filesystem-safe key so each business stays separate."""
    key = "".join(c.lower() if c.isalnum() else "-" for c in title).strip("-")
    while "--" in key:
        key = key.replace("--", "-")
    return key[:40] or "default"


def _ensure_project_dir(project: str, text: str) -> None:
    d = config.home() / "PROJECTS" / project
    if d.exists():
        return
    d.mkdir(parents=True, exist_ok=True)
    util.atomic_write(d / "README.md", "\n".join([
        f"# {project}",
        "",
        f"Captured {util.now()} by the owner.",
        "",
        "## What this is",
        text,
        "",
        "## Status",
        "Not yet triaged. Nothing here is validated.",
        "",
    ]))


def feedback(task_id: str, choice: str, note: str = "", *, source: str = "phone") -> dict:
    """One tap that actually moves the work."""
    row = tasks.get(task_id)
    if row is None:
        raise ValueError(f"no such task {task_id}")
    choice = (choice or "").strip().lower()
    if choice not in CHOICES:
        raise ValueError(f"choice must be one of {sorted(CHOICES)}")
    if note and security.scan_text(note):
        raise security.SecretLeak("That note looks like it contains a credential; nothing saved.")

    meaning, new_status = CHOICES[choice]
    clean_note = security.redact(note.strip())
    decision_id = memory.decide(
        f"owner feedback on {task_id}",
        f"{meaning}: {row['title']}",
        rationale=clean_note or f"one-tap '{choice}' from the {source}",
        evidence=f"task {task_id} was {row['status']} at the time",
        confidence="VERIFIED_FACT", made_by="owner")

    update = {"status": new_status}
    if choice == "yes":
        update["next_action"] = clean_note or row["next_action"] or "proceed as proposed"
        update["human_dependence"] = 0.5      # the owner has decided; it is unblocked
    elif choice == "no":
        update["last_error"] = f"owner said no: {clean_note or 'no reason given'}"
    else:
        update["blockers"] = f"deferred by the owner: {clean_note or 'no reason given'}"
    tasks.update(task_id, **update)
    db.log_event(source, f"feedback.{choice}", task_id, clean_note[:120])
    return {"status": "RECORDED", "task_id": task_id, "choice": choice,
            "task_status": new_status, "decision_id": decision_id,
            "message": f"{task_id} is now {new_status}."}


def feed(limit: int = 20) -> list[dict]:
    """What changed since the owner last looked — not a log dump."""
    conn = db.connect()
    rows = conn.execute(
        "SELECT task_id, title, evidence, completed_at FROM tasks "
        "WHERE status='DONE' AND completed_at IS NOT NULL "
        "ORDER BY completed_at DESC LIMIT ?", (limit,)).fetchall()
    items = [{"at": r["completed_at"], "type": "done", "title": r["title"],
              "detail": r["evidence"][:200], "ref": r["task_id"]} for r in rows]

    for r in conn.execute(
            "SELECT at, kind, amount_inr, description, stage FROM finance "
            "WHERE stage='ACTUAL' ORDER BY at DESC LIMIT ?", (limit,)):
        items.append({"at": r["at"], "type": "money",
                      "title": f"{r['kind']} INR {r['amount_inr']}",
                      "detail": r["description"], "ref": ""})

    for r in conn.execute(
            "SELECT created_at, error_id, component, message FROM errors "
            "WHERE status='OPEN' ORDER BY created_at DESC LIMIT ?", (limit,)):
        items.append({"at": r["created_at"], "type": "failure",
                      "title": f"{r['component']} failed",
                      "detail": r["message"][:200], "ref": r["error_id"]})

    for r in conn.execute(
            "SELECT at, decision_id, subject, decision FROM decisions "
            "ORDER BY at DESC LIMIT ?", (limit,)):
        items.append({"at": r["at"], "type": "decision", "title": r["subject"],
                      "detail": r["decision"][:200], "ref": r["decision_id"]})

    items.sort(key=lambda i: i["at"] or "", reverse=True)
    return [{k: security.redact(v) if isinstance(v, str) else v for k, v in item.items()}
            for item in items[:limit]]
