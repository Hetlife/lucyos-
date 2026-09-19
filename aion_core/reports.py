"""Owner-facing reports.  Mobile-first: short, factual, no log flooding.

Every renderer passes through security.redact before returning, so no report
can carry a credential into WhatsApp.
"""
from __future__ import annotations

import hashlib
import json

from . import (agents, approvals, config, db, errors, governor, memory, metrics,
               packets, resume, security, tasks, util)

AUDIT_GENESIS_HASH = "0" * 64
_AUDIT_CHAIN_FIELDS = ("id", "at", "day", "actor", "kind", "subject", "detail", "prev_hash")


def _clean(text: str) -> str:
    return security.redact(text)


def status() -> str:
    counts = tasks.counts()
    unblocked = len(tasks.ready(200))
    pend = approvals.pending()
    stalled = sum(tasks.progress(r["task_id"])["stalled"]
                  for state in tasks.ACTIVE_STATES for r in tasks.by_status(state))
    open_errs = errors.open_errors(limit=5)
    m = metrics.money()
    health = util.read_json(config.home() / "state" / "HEALTH.json", default={}) or {}
    healthy = health.get("healthy")
    nxt = tasks.next_task()
    paused = db.get_meta("paused", "0") == "1"
    safe = db.get_meta("safe_mode", "0") == "1"

    mode = []
    if paused:
        mode.append("PAUSED")
    if safe:
        mode.append("SAFE MODE")
    lines = [
        f"AION STATUS · {util.now()}",
        f"System: {'healthy' if healthy else ('degraded — ' + ', '.join(health.get('failing', [])) if health else 'never checked')}"
        + (f" · {' + '.join(mode)}" if mode else ""),
        f"Tasks: {unblocked} ready to run, {counts.get('RUNNING', 0)} running, "
        f"{counts.get('BLOCKED', 0) + counts.get('WAITING', 0)} blocked or waiting, "
        f"{counts.get('DONE', 0)} done",
        f"Money: ₹{m['real_revenue_inr']} real revenue, ₹{m['real_cost_inr']} cost, "
        f"₹{m['real_net_inr']} net",
        f"Approvals waiting: {', '.join(r['approval_id'] for r in pend) or 'none'}",
        f"Stalled without new evidence: {stalled}",
        f"Unresolved errors: {len(open_errs)}",
        f"Next action: {nxt['title'] if nxt else _nothing_runnable(counts)}",
    ]
    alert = governor.pending_alert()
    if alert:
        lines += ["", f"⚠ {alert}"]
    return _clean("\n".join(lines))



def execution_status(task_ids: list[str] | None = None) -> str:
    """Deterministic owner execution view from the canonical task ledger only.

    Transport-neutral: OpenClaw/WhatsApp may deliver this text, but they do not
    contribute task state. Evidence text and ledger timestamps are reported;
    worker/process counts are intentionally absent.
    """
    if task_ids:
        rows = [tasks.get(task_id) for task_id in task_ids]
        rows = [row for row in rows if row is not None]
    else:
        rows = []
        for state in ("RUNNING", "CLAIMED", "NEEDS_REVIEW", "NEEDS_APPROVAL",
                      "BLOCKED", "FAILED", "WAITING", "READY"):
            rows.extend(tasks.by_status(state))
        rows = rows[:12]
    lines = ["LucyOS · Execution"]
    for row in rows:
        status = row["status"]
        action = row["next_action"] or ""
        if "REVIEW_MERGE_READY" in action:
            status = "REVIEW_MERGE_READY"
        elif status == "NEEDS_REVIEW" and ("VERIFY" in action.upper() or "CI" in action.upper()):
            status = "VERIFYING"
        if row["status"] in tasks.ACTIVE_STATES and tasks.progress(row["task_id"])["stalled"]:
            status = "STALLED"
        evidence = (row["evidence"] or "No verified evidence yet").replace("\n", " ")
        evidence = evidence[:240] + ("…" if len(evidence) > 240 else "")
        lines += ["", f"{row['task_id']} — {status}", evidence,
                  f"Last ledger evidence: {row['updated_at']}",
                  f"Next: {action or 'No next action recorded'}"]
        if row["blockers"]:
            lines.append(f"Blocker: {row['blockers']}")
    counts = tasks.counts()
    stalled = sum(tasks.progress(r["task_id"])["stalled"]
                  for state in tasks.ACTIVE_STATES for r in tasks.by_status(state))
    owner = db.connect().execute(
        "SELECT COUNT(*) n FROM tasks WHERE status='NEEDS_APPROVAL' "
        "OR blockers LIKE 'OWNER_APPROVAL_REQUIRED:%'"
    ).fetchone()["n"]
    lines += ["", f"READY {counts.get('READY', 0)} · RUNNING {counts.get('RUNNING', 0)} · "
              f"REVIEW {counts.get('NEEDS_REVIEW', 0)} · STALLED {stalled} · FAILED {counts.get('FAILED', 0)}",
              "Need Het: " + (f"{owner} owner-gated task(s)" if owner else "Nothing")]
    return _clean("\n".join(lines))

def _nothing_runnable(counts: dict) -> str:
    """Say *why* nothing is runnable — 'queue empty' is usually a lie."""
    if counts.get("WAITING"):
        return f"{counts['WAITING']} task(s) waiting on an executor or recovery condition — send `blockers`"
    if counts.get("BLOCKED"):
        return f"{counts['BLOCKED']} task(s) blocked — send `blockers`"
    if counts.get("NEEDS_APPROVAL"):
        return "everything left needs your approval — send `blockers`"
    if counts.get("NEEDS_REVIEW"):
        return "remaining work is class C — it needs a strong-model session"
    return "queue empty — decompose the objective into executable tasks"


def today() -> str:
    day = util.today()
    conn = db.connect()
    rows = conn.execute(
        "SELECT kind, COUNT(*) c FROM events WHERE day=? GROUP BY kind ORDER BY c DESC",
        (day,)).fetchall()
    done = conn.execute(
        "SELECT task_id, title FROM tasks WHERE DATE(completed_at)=? ", (day,)).fetchall()
    errs = conn.execute(
        "SELECT error_id, message FROM errors WHERE DATE(created_at)=?", (day,)).fetchall()
    lines = [f"TODAY · {day}", ""]
    lines.append("Completed: " + (", ".join(f"{r['task_id']} {r['title']}" for r in done) or "nothing yet"))
    lines.append("Activity: " + (", ".join(f"{r['kind']} x{r['c']}" for r in rows) or "no recorded activity"))
    lines.append("New failures: " + (", ".join(r["error_id"] for r in errs) or "none"))
    lines.append(f"Model spend today: ₹{metrics.spend('day')}")
    return _clean("\n".join(lines))


def money() -> str:
    # Money is the canonical owner surface for financial progress.  Checking
    # here makes M0 (and later measured milestones) an automatic consequence
    # of recording evidenced ACTUAL revenue, rather than a separate claim.
    from . import milestones
    milestones.newly_reached()
    m0 = milestones.check()["M0"]
    m = metrics.money()
    b = metrics.budget_status()
    target = 100000.0
    pct = round(100 * m["real_net_inr"] / target, 2) if m["real_net_inr"] > 0 else 0.0
    lines = [
        "MONEY (real only unless labelled)",
        f"Mission: INR 1,00,000/month net - currently at {pct}% of it",
        f"Real revenue: ₹{m['real_revenue_inr']}",
        f"Real cost: ₹{m['real_cost_inr']} (incl. ₹{m['model_spend_month_inr']} model spend this month)",
        f"Real net: ₹{m['real_net_inr']}",
        f"M0 first real rupee: {'reached' if m0['reached'] else 'not reached'} — {m0['evidence']}",
        f"Reserve: ₹{m['reserve_inr']}",
        "",
        f"Model budget: ₹{b['day_spend_inr']}/{b['day_cap_inr']} today, "
        f"₹{b['month_spend_inr']}/{b['month_cap_inr']} this month",
        f"Strong-model build spend: ₹{b['strong_model_spend_inr']} of ₹{b['strong_model_cap_inr']} "
        f"({b['strong_model_pct']}%) · governor {b['governor']}",
    ]
    if m["non_actual"]:
        lines.append("")
        lines.append("Not real money (kept separate): " + "; ".join(
            f"{stage}: {vals}" for stage, vals in m["non_actual"].items()))
    return _clean("\n".join(lines))


def task_list(limit: int = 5) -> str:
    rows = tasks.ready(limit)
    if not rows:
        return "No ready tasks. Everything is blocked, waiting or done — send `blockers`."
    lines = ["TOP TASKS (by expected value)"]
    for r in rows:
        lines.append(f"{r['task_id']} · v{tasks.value(r)} · {r['title']}"
                     + (f" → {r['next_action']}" if r["next_action"] else ""))
    return _clean("\n".join(lines))


def blockers() -> str:
    pend = approvals.pending()
    blocked = tasks.blocked()
    lines = ["THINGS THAT NEED YOU"]
    if not pend and not blocked:
        return "Nothing needs you right now."
    for r in pend:
        lines.append("")
        lines.append(approvals.render(r))
    other = [t for t in blocked if t["status"] != "NEEDS_APPROVAL"]
    if other:
        lines.append("")
        lines.append("Blocked but not on you:")
        for t in other:
            lines.append(f"- {t['task_id']} {t['title']} ({t['status']}: {t['last_error'] or t['blockers'] or 'no reason recorded'})")
    return _clean("\n".join(lines))


def error_list(limit: int = 10) -> str:
    rows = errors.open_errors(limit)
    if not rows:
        return "No unresolved failures."
    lines = ["UNRESOLVED FAILURES"]
    for r in rows:
        lines.append(f"{r['error_id']} · {r['component']} · {r['kind']} · {r['message'][:120]}")
    return _clean("\n".join(lines))


def agent_list() -> str:
    lines = ["AGENTS"]
    for a in agents.all_agents():
        lines.append(f"{a['agent_id']} · class {a['model_class']} · {a['status']} · "
                     f"reliability {a['reliability']} · {a['runs']} runs / {a['failures']} failures"
                     + (f" · on {a['current_task']}" if a["current_task"] else ""))
    return _clean("\n".join(lines))


def full_report() -> str:
    r = resume.load()
    parts = [
        status(), "", task_list(5), "", blockers(), "", error_list(5), "", agent_list(), "",
        money(), "",
        "PACKETS: " + (", ".join(f"{k}={v}" for k, v in packets.stats().items()) or "none ingested"),
        f"BOTTLENECK: {r.get('bottleneck', 'not identified')}",
        f"RESUME POINT: {r.get('next_action', 'not set')}",
        f"LAST CHECKPOINT: {r.get('at', 'never')}",
    ]
    return _clean("\n".join(parts))


def render_markdown_surfaces() -> list[str]:
    """Regenerate the markdown views from the database.  Never hand-edited."""
    root = config.home()
    written = []

    written.append(str(util.atomic_write(root / "SYSTEM_STATE.md", "\n".join([
        "# SYSTEM STATE", "",
        "_Generated from the AION database. Do not hand-edit; edits are overwritten._", "",
        "```", status(), "```", "",
        "## Health", "```",
        _clean(str((util.read_json(root / "state" / "HEALTH.json", default={}) or {}).get("failing", "not checked"))),
        "```", "",
    ]))))

    rows = tasks.ready(50)
    lines = ["# GLOBAL TASKS", "", "| Task | Value | Status | Title | Next action |",
             "|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['task_id']} | {tasks.value(r)} | {r['status']} | {_clean(r['title'])} | "
                     f"{_clean(r['next_action'] or '')} |")
    lines += ["", "## Blocked / waiting", ""]
    for r in tasks.blocked():
        lines.append(f"- **{r['task_id']}** {_clean(r['title'])} — {r['status']} "
                     f"({_clean(r['last_error'] or r['blockers'] or 'no reason recorded')})")
    written.append(str(util.atomic_write(root / "GLOBAL_TASKS.md", "\n".join(lines) + "\n")))

    lines = ["# APPROVALS", "", "Reply in WhatsApp with `APPROVE <ID>` or `DENY <ID>`.", ""]
    pend = approvals.pending()
    if not pend:
        lines.append("_No approval is currently pending._")
    for r in pend:
        lines += ["```", approvals.render(r), "```", ""]
    decided = db.connect().execute(
        "SELECT * FROM approvals WHERE status!='PENDING' ORDER BY decided_at DESC LIMIT 20").fetchall()
    if decided:
        lines += ["## Decided", ""]
        for r in decided:
            lines.append(f"- {r['approval_id']} — {r['status']} by {r['decided_by']} "
                         f"at {r['decided_at']} — {_clean(r['action'])}")
    written.append(str(util.atomic_write(root / "APPROVALS.md", "\n".join(lines) + "\n")))

    lines = ["# DECISIONS", ""]
    for d in memory.decisions(100):
        lines += [f"## {d['decision_id']} — {_clean(d['subject'])}",
                  f"- **When**: {d['at']}  ·  **By**: {d['made_by']}  ·  **Confidence**: {d['confidence']}",
                  f"- **Decision**: {_clean(d['decision'])}",
                  f"- **Rationale**: {_clean(d['rationale'] or 'not recorded')}",
                  f"- **Evidence**: {_clean(d['evidence'] or 'none recorded')}", ""]
    written.append(str(util.atomic_write(root / "DECISIONS.md", "\n".join(lines) + "\n")))

    lines = ["# BLOCKERS", "", "```", blockers(), "```", ""]
    written.append(str(util.atomic_write(root / "BLOCKERS.md", "\n".join(lines))))
    return written


def _audit_record_hash(record: dict) -> str:
    payload = json.dumps({k: record[k] for k in _AUDIT_CHAIN_FIELDS}, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def audit_export() -> list[dict]:
    """Export every `events` row, oldest first, exactly as written -- this is
    a read-only export, never a rewrite of the events table itself. Each
    record carries prev_hash (the previous record's hash) and its own hash
    over its fields plus prev_hash, forming a hash chain: `audit_verify()`
    can then detect a modified, deleted, or naively-inserted record in the
    exported chain without needing the live database."""
    rows = db.connect().execute(
        "SELECT id, at, day, actor, kind, subject, detail FROM events ORDER BY id ASC"
    ).fetchall()
    chain = []
    prev_hash = AUDIT_GENESIS_HASH
    for row in rows:
        record = {k: row[k] for k in ("id", "at", "day", "actor", "kind", "subject", "detail")}
        record["prev_hash"] = prev_hash
        record["hash"] = _audit_record_hash(record)
        chain.append(record)
        prev_hash = record["hash"]
    return chain


def audit_verify(chain: list[dict]) -> dict:
    """Walk an exported chain and confirm every link and every hash.  A
    record whose fields were edited fails its own hash check; a deleted
    record breaks the next record's prev_hash link; an inserted record
    (without the attacker re-deriving every following hash by hand) breaks
    the link the same way.  This proves the exported chain is internally
    tamper-evident -- it does not, on its own, prove the export still
    matches the live `events` table (a re-export and diff does that)."""
    if not chain:
        return {"ok": True, "detail": "empty chain", "records": 0}
    prev_hash = AUDIT_GENESIS_HASH
    for i, record in enumerate(chain):
        if not all(k in record for k in _AUDIT_CHAIN_FIELDS) or "hash" not in record:
            return {"ok": False, "detail": f"record {i}: missing required field(s)",
                     "records": len(chain), "broken_at": i}
        if record["prev_hash"] != prev_hash:
            return {"ok": False,
                     "detail": f"record {i} (id={record.get('id')}): prev_hash link broken "
                               "-- a record was deleted, reordered, or inserted",
                     "records": len(chain), "broken_at": i}
        expected = _audit_record_hash(record)
        if record["hash"] != expected:
            return {"ok": False,
                     "detail": f"record {i} (id={record.get('id')}): hash does not match its "
                               "own fields -- record was modified",
                     "records": len(chain), "broken_at": i}
        prev_hash = record["hash"]
    return {"ok": True, "detail": f"chain of {len(chain)} record(s) verified intact", "records": len(chain)}


def routing_report() -> dict:
    """Deterministic SQL report over model_usage -- no model or API call is
    ever made to produce this.  With no usage recorded, this says so
    explicitly rather than reporting a fabricated zero-cost summary."""
    conn = db.connect()
    total_calls = conn.execute("SELECT COUNT(*) c FROM model_usage").fetchone()["c"]
    if not total_calls:
        return {"total_calls": 0, "detail": "no usage recorded", "by_class": [], "by_model": []}

    totals = conn.execute(
        "SELECT COUNT(*) n, COALESCE(SUM(input_tokens),0) in_tok, "
        "COALESCE(SUM(output_tokens),0) out_tok, COALESCE(SUM(cost_inr),0) cost, "
        "COALESCE(SUM(retries),0) retries, COALESCE(SUM(escalated),0) escalated, "
        "COALESCE(SUM(CASE WHEN success=0 THEN 1 ELSE 0 END),0) failures "
        "FROM model_usage"
    ).fetchone()

    by_class = [
        {
            "model_class": r["model_class"], "calls": r["n"], "cost_inr": round(r["cost"], 2),
            "input_tokens": r["in_tok"], "output_tokens": r["out_tok"],
            "retries": r["retries"], "escalations": r["escalated"], "failures": r["failures"],
        }
        for r in conn.execute(
            "SELECT model_class, COUNT(*) n, COALESCE(SUM(input_tokens),0) in_tok, "
            "COALESCE(SUM(output_tokens),0) out_tok, COALESCE(SUM(cost_inr),0) cost, "
            "COALESCE(SUM(retries),0) retries, COALESCE(SUM(escalated),0) escalated, "
            "COALESCE(SUM(CASE WHEN success=0 THEN 1 ELSE 0 END),0) failures "
            "FROM model_usage GROUP BY model_class ORDER BY model_class"
        ).fetchall()
    ]

    by_model = [
        {
            "model": r["model"], "model_class": r["model_class"], "calls": r["n"],
            "cost_inr": round(r["cost"], 2), "input_tokens": r["in_tok"], "output_tokens": r["out_tok"],
        }
        for r in conn.execute(
            "SELECT model, model_class, COUNT(*) n, COALESCE(SUM(cost_inr),0) cost, "
            "COALESCE(SUM(input_tokens),0) in_tok, COALESCE(SUM(output_tokens),0) out_tok "
            "FROM model_usage GROUP BY model, model_class ORDER BY cost DESC, model ASC"
        ).fetchall()
    ]

    return {
        "total_calls": totals["n"],
        "total_cost_inr": round(totals["cost"], 2),
        "total_input_tokens": totals["in_tok"],
        "total_output_tokens": totals["out_tok"],
        "total_escalations": totals["escalated"],
        "total_retries": totals["retries"],
        "total_failures": totals["failures"],
        "by_class": by_class,
        "by_model": by_model,
        "detail": f"{totals['n']} call(s), ₹{round(totals['cost'], 2)} total cost, "
                  f"{totals['escalated']} escalated",
    }
