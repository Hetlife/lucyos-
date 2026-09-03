"""Owner-facing reports.  Mobile-first: short, factual, no log flooding.

Every renderer passes through security.redact before returning, so no report
can carry a credential into WhatsApp.
"""
from __future__ import annotations

from . import (agents, approvals, config, db, errors, memory, metrics, packets,
               resume, security, tasks, util)


def _clean(text: str) -> str:
    return security.redact(text)


def status() -> str:
    counts = tasks.counts()
    pend = approvals.pending()
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
        f"Tasks: {counts.get('READY', 0)} ready, {counts.get('RUNNING', 0)} running, "
        f"{counts.get('BLOCKED', 0)} blocked, {counts.get('DONE', 0)} done",
        f"Money: ₹{m['real_revenue_inr']} real revenue, ₹{m['real_cost_inr']} cost, "
        f"₹{m['real_net_inr']} net",
        f"Approvals waiting: {', '.join(r['approval_id'] for r in pend) or 'none'}",
        f"Unresolved errors: {len(open_errs)}",
        f"Next action: {nxt['title'] if nxt else 'queue empty — needs triage'}",
    ]
    return _clean("\n".join(lines))


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
    m = metrics.money()
    b = metrics.budget_status()
    lines = [
        "MONEY (real only unless labelled)",
        f"Real revenue: ₹{m['real_revenue_inr']}",
        f"Real cost: ₹{m['real_cost_inr']} (incl. ₹{m['model_spend_month_inr']} model spend this month)",
        f"Real net: ₹{m['real_net_inr']}",
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
