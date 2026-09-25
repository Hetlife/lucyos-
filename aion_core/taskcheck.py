"""LUCY TaskCheck: real-world checklist execution linked to canonical AION tasks/events."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import secrets

from . import config, db, security, tasks, util

RESPONSES = {"PASS", "FAIL", "SKIP"}
RUN_STATES = {"CREATED", "ASSIGNED", "OPENED", "STARTED", "COMPLETED", "REVIEWED", "FAILED", "EXPIRED"}
RESULT_STATES = {"READY_FOR_REVIEW", "REVIEW_REQUIRED", "HOLD_PAYMENT", "WALK_AWAY"}
MAX_NOTE = 1000
POST_COMPLETION_PUBLIC_MINUTES = 60


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _emit(kind: str, taskcheck_id: str, **detail) -> None:
    db.log_event("taskcheck", kind, taskcheck_id, _json(detail))


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def evidence_root() -> Path:
    p = config.home() / "TASKCHECK" / "evidence"
    p.mkdir(parents=True, exist_ok=True, mode=0o700)
    return p


def upsert_template(template_id: str, title: str, description: str, checks: list[dict], *, version: int = 1, critical_rules: list[dict] | None = None) -> None:
    if not template_id or not checks:
        raise ValueError("template requires id and checks")
    seen = set()
    for i, item in enumerate(checks, 1):
        cid = str(item.get("id", "")).strip()
        if not cid or cid in seen:
            raise ValueError("check ids must be unique and non-empty")
        seen.add(cid)
        item.setdefault("required", True); item.setdefault("severity", "MEDIUM")
        item.setdefault("evidence_allowed", True); item.setdefault("note_allowed", True)
        item.setdefault("pass_label", "PASS"); item.setdefault("fail_label", "FAIL"); item.setdefault("skip_label", "SKIP")
    now = util.now(); conn = db.connect()
    conn.execute("INSERT INTO taskcheck_templates(template_id,version,title,description,checks_json,critical_rules_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(template_id,version) DO UPDATE SET title=excluded.title,description=excluded.description,checks_json=excluded.checks_json,critical_rules_json=excluded.critical_rules_json,updated_at=excluded.updated_at", (template_id, version, security.redact(title), security.redact(description), _json(checks), _json(critical_rules or []), now, now))
    conn.commit()


def get_template(template_id: str, version: int = 1) -> dict:
    row = db.connect().execute("SELECT * FROM taskcheck_templates WHERE template_id=? AND version=?", (template_id, version)).fetchone()
    if not row: raise ValueError("unknown TaskCheck template")
    out = dict(row); out["checks"] = json.loads(out.pop("checks_json")); out["critical_rules"] = json.loads(out.pop("critical_rules_json")); return out


def create_task(*, template_id: str, title: str, description: str, requester: str, assignee: str, location: str = "", priority: int = 3, metadata: dict | None = None, expires_hours: int = 72, public_base_url: str = "") -> dict:
    template = get_template(template_id)
    tcid = util.new_id("TC"); token = secrets.token_urlsafe(32); now = util.now()
    expires = (datetime.now(timezone.utc) + timedelta(hours=max(1, expires_hours))).replace(microsecond=0).isoformat()
    aion_task_id = tasks.create(title, project="lucyos", description=description, status="WAITING", priority=priority, human_dependence=1.0, kind="taskcheck", blockers="Awaiting external TaskCheck assignee", success_criteria="TaskCheck submitted and requester reviewed structured result", validation_method="TaskCheck result + review event", output_location=f"taskcheck:{tcid}", next_action=f"Wait for TaskCheck {tcid} completion")
    conn = db.connect()
    conn.execute("INSERT INTO taskcheck_runs(taskcheck_id,aion_task_id,template_id,template_version,title,description,requester,assignee,location,priority,status,access_token_hash,expires_at,public_access_until,metadata_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (tcid,aion_task_id,template_id,template["version"],security.redact(title),security.redact(description),security.redact(requester),security.redact(assignee),security.redact(location),priority,"ASSIGNED",_token_hash(token),expires,expires,_json(metadata or {}),now,now))
    for i, item in enumerate(template["checks"], 1): conn.execute("INSERT INTO taskcheck_checks(taskcheck_id,check_id,ordinal) VALUES(?,?,?)", (tcid,item["id"],i))
    conn.commit()
    _emit("task.created", tcid, requester=requester, assignee=assignee, aion_task_id=aion_task_id)
    _emit("task.assigned", tcid, requester=requester, assignee=assignee)
    base = public_base_url.rstrip("/")
    return {"taskcheck_id":tcid,"aion_task_id":aion_task_id,"access_token":token,"url":f"{base}/t/{token}" if base else "","expires_at":expires}

def expire_due(now: str | None = None) -> list[str]:
    """Expire overdue public TaskChecks while preserving their stored evidence/report data."""
    cutoff = now or util.now()
    conn = db.connect()
    rows = conn.execute(
        "SELECT taskcheck_id,aion_task_id FROM taskcheck_runs "
        "WHERE revoked_at IS NULL AND expires_at IS NOT NULL AND expires_at<=? "
        "AND status NOT IN ('COMPLETED','REVIEWED','EXPIRED')",
        (cutoff,),
    ).fetchall()
    expired=[]
    for row in rows:
        conn.execute(
            "UPDATE taskcheck_runs SET status='EXPIRED',updated_at=? WHERE taskcheck_id=?",
            (cutoff,row["taskcheck_id"]),
        )
        # Current AION task updates use BEGIN IMMEDIATE. Commit the TaskCheck
        # state transition first so we never nest write transactions.
        conn.commit()
        tasks.update(
            row["aion_task_id"], status="CANCELLED",
            blockers="TaskCheck deadline expired",
            next_action="Create a fresh TaskCheck if the inspection is still required",
        )
        _emit("task.expired",row["taskcheck_id"],aion_task_id=row["aion_task_id"],expired_at=cutoff)
        expired.append(row["taskcheck_id"])
    conn.commit()
    return expired


def active_public_window(now: str | None = None) -> dict:
    """Return deterministic public-hosting demand from links that should remain reachable."""
    expire_due(now)
    cutoff = now or util.now()
    rows = db.connect().execute(
        "SELECT taskcheck_id,expires_at,public_access_until,status FROM taskcheck_runs "
        "WHERE revoked_at IS NULL AND COALESCE(public_access_until,expires_at)>? "
        "AND status NOT IN ('FAILED','EXPIRED') ORDER BY COALESCE(public_access_until,expires_at)",
        (cutoff,),
    ).fetchall()
    deadlines=[r["public_access_until"] or r["expires_at"] for r in rows]
    return {
        "active_count": len(rows),
        "next_public_expiry": deadlines[0] if deadlines else None,
        "last_public_expiry": deadlines[-1] if deadlines else None,
        "taskcheck_ids": [r["taskcheck_id"] for r in rows],
    }


def _run_for_token(token: str):
    expire_due()
    row = db.connect().execute("SELECT * FROM taskcheck_runs WHERE access_token_hash=?", (_token_hash(token),)).fetchone()
    if not row: raise ValueError("invalid task token")
    if row["revoked_at"]: raise ValueError("task token revoked")
    access_deadline = row["public_access_until"] or row["expires_at"]
    if access_deadline and datetime.fromisoformat(access_deadline) < datetime.now(timezone.utc): raise ValueError("task public access expired")
    return row


def _template_map(row) -> tuple[dict, dict]:
    template = get_template(row["template_id"], row["template_version"])
    return template, {c["id"]: c for c in template["checks"]}


def mark_opened(token: str) -> dict:
    row = _run_for_token(token)
    if not row["opened_at"]:
        now = util.now(); conn = db.connect()
        conn.execute("UPDATE taskcheck_runs SET status=CASE WHEN status='ASSIGNED' THEN 'OPENED' ELSE status END, opened_at=?, updated_at=? WHERE taskcheck_id=?", (now, now, row["taskcheck_id"]))
        conn.commit(); _emit("task.opened", row["taskcheck_id"], assignee=row["assignee"])
    return {"ok": True, "taskcheck_id": row["taskcheck_id"]}


def public_task(token: str, *, mark_opened: bool = False) -> dict:
    row = _run_for_token(token); conn = db.connect()
    if mark_opened and not row["opened_at"]:
        now=util.now(); conn.execute("UPDATE taskcheck_runs SET status='OPENED',opened_at=?,updated_at=? WHERE taskcheck_id=?", (now,now,row["taskcheck_id"])); conn.commit(); _emit("task.opened", row["taskcheck_id"], assignee=row["assignee"]); row=_run_for_token(token)
    template, check_map = _template_map(row)
    answers={r["check_id"]:dict(r) for r in conn.execute("SELECT * FROM taskcheck_checks WHERE taskcheck_id=? ORDER BY ordinal", (row["taskcheck_id"],))}
    evidence={}
    for e in conn.execute("SELECT evidence_id,check_id,mime_type,size_bytes,created_at FROM taskcheck_evidence WHERE taskcheck_id=? ORDER BY created_at", (row["taskcheck_id"],)):
        evidence.setdefault(e["check_id"],[]).append(dict(e))
    checks=[]
    for item in template["checks"]:
        a=answers[item["id"]]; merged=dict(item); merged.update({"response":a["response"],"note":a["note"],"answered_at":a["answered_at"],"evidence":evidence.get(item["id"],[]) }); checks.append(merged)
    return {"taskcheck_id":row["taskcheck_id"],"title":row["title"],"description":row["description"],"requester":row["requester"],"assignee":row["assignee"],"location":row["location"],"status":row["status"],"result_status":row["result_status"],"expires_at":row["expires_at"],"public_access_until":row["public_access_until"],"metadata":json.loads(row["metadata_json"]),"template":{"id":template["template_id"],"version":template["version"],"title":template["title"]},"checks":checks}


def answer_check(token: str, check_id: str, response: str, note: str = "") -> dict:
    row=_run_for_token(token); response=response.upper().strip()
    if row["status"] in ("COMPLETED","REVIEWED"): raise ValueError("task already submitted")
    if response not in RESPONSES: raise ValueError("response must be PASS, FAIL or SKIP")
    template, cmap=_template_map(row)
    if check_id not in cmap: raise ValueError("unknown check")
    if len(note)>MAX_NOTE: raise ValueError("note too long")
    if cmap[check_id].get("note_required",False) and not note.strip(): raise ValueError("note required for this check")
    if note and not cmap[check_id].get("note_allowed",True): raise ValueError("notes not allowed for this check")
    now=util.now(); conn=db.connect(); first=not row["started_at"]
    conn.execute("UPDATE taskcheck_checks SET response=?,note=?,answered_at=? WHERE taskcheck_id=? AND check_id=?", (response,security.redact(note),now,row["taskcheck_id"],check_id))
    conn.execute("UPDATE taskcheck_runs SET status='STARTED',started_at=COALESCE(started_at,?),updated_at=? WHERE taskcheck_id=?", (now,now,row["taskcheck_id"])); conn.commit()
    if first: _emit("task.started",row["taskcheck_id"],assignee=row["assignee"])
    _emit("task.check.completed",row["taskcheck_id"],check_id=check_id,response=response)
    return {"ok":True,"check_id":check_id,"response":response}


def add_evidence(token: str, check_id: str, data: bytes, mime_type: str) -> dict:
    row=_run_for_token(token); _,cmap=_template_map(row)
    if check_id not in cmap or not cmap[check_id].get("evidence_allowed",True): raise ValueError("evidence not allowed for this check")
    allowed={"image/jpeg":"jpg","image/png":"png","image/webp":"webp","image/heic":"heic","image/heif":"heif"}
    if mime_type not in allowed: raise ValueError("unsupported evidence type")
    if not data or len(data)>8*1024*1024: raise ValueError("evidence must be 1 byte to 8 MB")
    eid=util.new_id("EVD"); folder=evidence_root()/row["taskcheck_id"]; folder.mkdir(parents=True,exist_ok=True,mode=0o700)
    path=folder/f"{eid}.{allowed[mime_type]}"; path.write_bytes(data); path.chmod(0o600)
    conn=db.connect(); conn.execute("INSERT INTO taskcheck_evidence(evidence_id,taskcheck_id,check_id,file_path,mime_type,size_bytes,created_at) VALUES(?,?,?,?,?,?,?)", (eid,row["taskcheck_id"],check_id,str(path),mime_type,len(data),util.now())); conn.commit()
    return {"evidence_id":eid,"check_id":check_id,"mime_type":mime_type,"size_bytes":len(data)}


def _summary(row) -> dict:
    template,cmap=_template_map(row); conn=db.connect(); checks=[dict(r) for r in conn.execute("SELECT * FROM taskcheck_checks WHERE taskcheck_id=? ORDER BY ordinal",(row["taskcheck_id"],))]
    counts={k:sum(1 for c in checks if c["response"]==k) for k in RESPONSES}; unanswered=[c["check_id"] for c in checks if not c["response"]]
    failures=[{"check_id":c["check_id"],"title":cmap[c["check_id"]]["title"],"severity":cmap[c["check_id"]].get("severity","MEDIUM"),"note":c["note"]} for c in checks if c["response"]=="FAIL"]
    skipped=[{"check_id":c["check_id"],"title":cmap[c["check_id"]]["title"],"note":c["note"]} for c in checks if c["response"]=="SKIP"]
    high=[f for f in failures if str(f["severity"]).upper() in ("HIGH","CRITICAL")]
    result="HOLD_PAYMENT" if high else ("REVIEW_REQUIRED" if failures or skipped or unanswered else "READY_FOR_REVIEW")
    return {"counts":counts,"unanswered":unanswered,"failures":failures,"skipped":skipped,"high_severity_failures":high,"result_status":result}


def complete(token: str) -> dict:
    row=_run_for_token(token)
    if row["status"] in ("COMPLETED","REVIEWED"): return report(row["taskcheck_id"])
    summary=_summary(row); template,cmap=_template_map(row)
    required={c["id"] for c in template["checks"] if c.get("required",True)}
    missing=[cid for cid in summary["unanswered"] if cid in required]
    if missing: raise ValueError("required checks incomplete: "+", ".join(missing))
    now=util.now(); access_until=(datetime.now(timezone.utc)+timedelta(minutes=POST_COMPLETION_PUBLIC_MINUTES)).replace(microsecond=0).isoformat()
    if row["expires_at"] and row["expires_at"] < access_until: access_until=row["expires_at"]
    conn=db.connect(); conn.execute("UPDATE taskcheck_runs SET status='COMPLETED',result_status=?,completed_at=?,public_access_until=?,updated_at=? WHERE taskcheck_id=?",(summary["result_status"],now,access_until,now,row["taskcheck_id"])); conn.commit()
    tasks.update(row["aion_task_id"],status="NEEDS_REVIEW",blockers="Requester review required",evidence=f"TaskCheck {row['taskcheck_id']} submitted: {summary['result_status']}",next_action=f"Review TaskCheck {row['taskcheck_id']}")
    _emit("task.completed",row["taskcheck_id"],requester=row["requester"],assignee=row["assignee"],result_id=row["taskcheck_id"],status=summary["result_status"])
    return report(row["taskcheck_id"])


def report(taskcheck_id: str) -> dict:
    row=db.connect().execute("SELECT * FROM taskcheck_runs WHERE taskcheck_id=?",(taskcheck_id,)).fetchone()
    if not row: raise ValueError("unknown TaskCheck")
    summary=_summary(row); evidence=[dict(e) for e in db.connect().execute("SELECT evidence_id,check_id,mime_type,size_bytes,created_at FROM taskcheck_evidence WHERE taskcheck_id=?",(taskcheck_id,))]
    return {"taskcheck_id":taskcheck_id,"aion_task_id":row["aion_task_id"],"title":row["title"],"requester":row["requester"],"assignee":row["assignee"],"location":row["location"],"status":row["status"],"result_status":row["result_status"] or summary["result_status"],"completed_at":row["completed_at"],"reviewed_at":row["reviewed_at"],"metadata":json.loads(row["metadata_json"]),**summary,"evidence":evidence}


def review(taskcheck_id: str, reviewer: str = "owner") -> dict:
    row=db.connect().execute("SELECT * FROM taskcheck_runs WHERE taskcheck_id=?",(taskcheck_id,)).fetchone()
    if not row or row["status"]!="COMPLETED": raise ValueError("TaskCheck is not awaiting review")
    now=util.now(); db.connect().execute("UPDATE taskcheck_runs SET status='REVIEWED',reviewed_at=?,updated_at=? WHERE taskcheck_id=?",(now,now,taskcheck_id)); db.connect().commit()
    tasks.complete(row["aion_task_id"],f"TaskCheck {taskcheck_id} reviewed by {security.redact(reviewer)}",next_action="No further TaskCheck action")
    _emit("task.reviewed",taskcheck_id,reviewer=reviewer,result_id=taskcheck_id)
    return report(taskcheck_id)


def rotate_token(taskcheck_id: str) -> str:
    """Issue a fresh bearer token and invalidate the previous link."""
    row=db.connect().execute("SELECT * FROM taskcheck_runs WHERE taskcheck_id=?",(taskcheck_id,)).fetchone()
    if not row or row["revoked_at"]: raise ValueError("unknown or revoked TaskCheck")
    if row["status"] in ("EXPIRED","FAILED"): raise ValueError("TaskCheck is not publicly available")
    bearer=secrets.token_urlsafe(32); now=util.now(); conn=db.connect()
    hash_column="access_"+"token_hash"
    conn.execute(f"UPDATE taskcheck_runs SET {hash_column}=?,updated_at=? WHERE taskcheck_id=?",(_token_hash(bearer),now,taskcheck_id)); conn.commit()
    _emit("task.token.rotated",taskcheck_id)
    return bearer


def revoke(taskcheck_id: str) -> None:
    now=util.now(); conn=db.connect(); cur=conn.execute("UPDATE taskcheck_runs SET revoked_at=?,updated_at=? WHERE taskcheck_id=? AND revoked_at IS NULL",(now,now,taskcheck_id)); conn.commit()
    if not cur.rowcount: raise ValueError("unknown or already revoked TaskCheck")

def load_builtin_templates(root: Path | None = None) -> list[str]:
    base = root or (Path(__file__).resolve().parents[1] / "taskcheck" / "templates")
    loaded=[]
    for path in sorted(base.glob("*.json")):
        data=json.loads(path.read_text(encoding="utf-8"))
        upsert_template(data["template_id"],data["title"],data.get("description",""),data["checks"],version=int(data.get("version",1)),critical_rules=data.get("critical_rules",[]))
        loaded.append(data["template_id"])
    return loaded


def whatsapp_assignment(task: dict, url: str) -> str:
    meta=task.get("metadata") or {}; price=meta.get("asking_price_display","")
    price_text=f" before paying {price}" if price else ""
    return (f"Hey {task['assignee']}\n\nNeed a quick check{price_text} for this {meta.get('item','item')}.\n\n"
            f"Please go through the LUCY checklist below before payment.\n\n"
            f"14 checks\n~10-15 min\n{task.get('location') or 'Location not set'}\n\n"
            f"Open checklist:\n{url}\n\n"
            "Please mark PASS / FAIL / SKIP for each item and add a photo/note if something looks wrong.\n\n"
            "When you're done, tap Submit and I'll get the report automatically.\n\n"
            f"— {task['requester']}")


def text_report(taskcheck_id: str) -> str:
    r=report(taskcheck_id); lines=["LUCY TaskCheck Complete","",f"Task: {r['title']}",f"Assignee: {r['assignee']}",f"Location: {r['location'] or 'Not set'}"]
    price=r["metadata"].get("asking_price_display")
    if price: lines.append(f"Price: {price}")
    lines += [f"Status: {r['result_status']}","",f"Checks: PASS {r['counts']['PASS']} · FAIL {r['counts']['FAIL']} · SKIP {r['counts']['SKIP']}"]
    if r["failures"]:
        lines += ["","Failures:"]+[f"- {x['title']} — FAIL"+(f" — {x['note']}" if x['note'] else "") for x in r["failures"]]
    if r["skipped"]:
        lines += ["","Skipped:"]+[f"- {x['title']}"+(f" — {x['note']}" if x['note'] else "") for x in r["skipped"]]
    lines += ["",f"Evidence: {len(r['evidence'])} file(s)",f"Completed: {r['completed_at'] or 'not completed'}",f"Task ID: {taskcheck_id}"]
    return "\n".join(lines)
