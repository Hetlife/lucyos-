"""Revenue experiments: measured funnels with a verdict the code computes.

An experiment is a folder under `PROJECTS/<project>/experiments/<EXP-ID>-*/`
in the repository (durable, phone-readable on GitHub) holding:

  experiment.json   the rules — window, thresholds, the decision each outcome forces
  contacts.csv      the funnel log the owner fills in, one row per contact,
                    by CODE only (never a name or a number)

The evidenced count of payments comes from the `finance` table, never from the
CSV: a `paid=1` cell is a claim, an ACTUAL revenue row with a transaction
reference is a fact.  The verdict below is computed from facts, so the plan
step that "evaluates the experiment" cannot be marked DONE early and nobody
has to remember the rules.

Nothing here knows about any one business: the folder layout and the JSON
are the contract, exactly as `sevaa.py` is the contract for one integration.
"""
from __future__ import annotations

import csv
import json
import os
from datetime import date, timedelta
from pathlib import Path

from . import db, util

STATES = ("NOT_STARTED", "RUNNING", "EXTENDED", "SUCCESS", "FAILURE", "BLOCKED")
DECIDED = ("SUCCESS", "FAILURE")


class ExperimentError(Exception):
    pass


def root() -> Path:
    """Where experiment folders live.  Overridable so tests use a temp tree."""
    env = os.environ.get("AION_PROJECTS_DIR")
    if env:
        return Path(env).expanduser()
    return Path(__file__).resolve().parent.parent / "PROJECTS"


def _folders() -> list[Path]:
    base = root()
    if not base.is_dir():
        return []
    return sorted(p.parent for p in base.glob("*/experiments/*/experiment.json"))


def find(experiment_id: str) -> Path:
    for folder in _folders():
        spec = _load_spec(folder)
        if spec.get("experiment_id", "").upper() == experiment_id.upper():
            return folder
    raise ExperimentError(f"no experiment {experiment_id} under {root()}")


def _load_spec(folder: Path) -> dict:
    try:
        return json.loads((folder / "experiment.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExperimentError(f"{folder / 'experiment.json'}: {exc}") from exc


def _rows(folder: Path, spec: dict) -> list[dict]:
    log = folder / spec.get("funnel_log", "contacts.csv")
    if not log.is_file():
        return []
    with log.open(encoding="utf-8", newline="") as fh:
        return [r for r in csv.DictReader(fh) if (r.get("contact_code") or "").strip()]


def _parse_day(text: str) -> date | None:
    text = (text or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _evidenced_payments(prefix: str) -> list:
    if not prefix:
        return []
    return db.connect().execute(
        "SELECT description, amount_inr, evidence, day FROM finance "
        "WHERE kind='revenue' AND stage='ACTUAL' AND evidence!='' AND description LIKE ? "
        "ORDER BY at", (prefix + "%",)).fetchall()


def status(experiment_id: str, *, today: date | None = None) -> dict:
    """Funnel counts plus the verdict the rules force.  Reads only real rows."""
    folder = find(experiment_id)
    spec = _load_spec(folder)
    rows = _rows(folder, spec)
    today = today or date.today()

    sent_days = [d for d in (_parse_day(r.get("sent_at")) for r in rows) if d]
    sent = len(sent_days)
    replied = sum(1 for r in rows if (r.get("reply") or "").strip())
    interested = sum(1 for r in rows if (r.get("reply") or "").strip().lower() == "interested")
    claimed_paid = sum(1 for r in rows if (r.get("paid") or "").strip() == "1")
    reasons: dict = {}
    for r in rows:
        code = (r.get("reason_code") or "").strip().lower()
        if code:
            reasons[code] = reasons.get(code, 0) + 1
    top_reason = max(reasons, key=reasons.get) if reasons else None

    payments = _evidenced_payments(spec.get("revenue_description_prefix", ""))
    paid = len(payments)
    revenue = round(sum(p["amount_inr"] for p in payments), 2)

    started = min(sent_days) if sent_days else None
    window_days = int(spec.get("window_days", 14))
    amb = spec.get("ambiguous") or {}
    extended = False
    window_end = None
    day = None
    if started:
        window_end = started + timedelta(days=window_days)
        day = (today - started).days + 1

    success_min = int((spec.get("success") or {}).get("paid_min", 1))
    failure_max = int((spec.get("failure") or {}).get("paid_max", 0))
    min_contacts = int(spec.get("min_contacts", 0))
    contacts_deadline = int(spec.get("min_contacts_deadline_days", window_days))

    if not started:
        state = "NOT_STARTED"
    elif paid >= success_min:
        state = "SUCCESS"
    elif sent < min_contacts and day > contacts_deadline:
        state = "BLOCKED"
    elif today <= window_end:
        state = "RUNNING"
    else:
        # Window closed without success.
        if paid <= failure_max:
            state = "FAILURE"
        elif amb:
            extended = True
            window_end = started + timedelta(days=window_days + int(amb.get("extend_days", 0)))
            then_min = int(amb.get("then_paid_min", success_min))
            if paid >= then_min:
                state = "SUCCESS"
            elif today <= window_end:
                state = "EXTENDED"
            else:
                state = "FAILURE"
        else:
            state = "FAILURE"

    decision = _decision_text(spec, state, replied, top_reason)
    return {
        "experiment_id": spec.get("experiment_id"),
        "project": spec.get("project"),
        "title": spec.get("title"),
        "folder": str(folder),
        "price_inr": spec.get("offer_price_inr"),
        "state": state,
        "decided": state in DECIDED,
        "extended": extended,
        "started_at": started.isoformat() if started else None,
        "day": day,
        "window_days": window_days + (int(amb.get("extend_days", 0)) if extended else 0),
        "window_end": window_end.isoformat() if window_end else None,
        "sent": sent,
        "min_contacts": min_contacts,
        "replied": replied,
        "interested": interested,
        "claimed_paid": claimed_paid,
        "paid": paid,
        "revenue_inr": revenue,
        "success_paid_min": success_min,
        "top_reason": top_reason,
        "reasons": reasons,
        "decision": decision,
        "measured_at": util.now(),
    }


def _decision_text(spec: dict, state: str, replied: int, top_reason: str | None) -> str:
    decisions = spec.get("decisions") or {}
    if state == "FAILURE":
        if replied >= 5 and top_reason == "price" and decisions.get("FAILURE_price"):
            return decisions["FAILURE_price"]
        return decisions.get("FAILURE_offer") or decisions.get("FAILURE", "")
    if state == "EXTENDED":
        return decisions.get("AMBIGUOUS", "")
    return decisions.get(state, "")


def all_status() -> list[dict]:
    out = []
    for folder in _folders():
        spec = _load_spec(folder)
        try:
            out.append(status(spec["experiment_id"]))
        except ExperimentError:
            continue
    return out


def line(s: dict) -> str:
    """One line for `status` and the phone card."""
    where = f"day {s['day']}/{s['window_days']}" if s["day"] else "not started"
    return (f"{s['experiment_id']}: {s['state']} · {s['sent']}/{s['min_contacts']} sent, "
            f"{s['replied']} replied, {s['paid']} paid (₹{s['revenue_inr']:.0f} evidenced) · {where}")


def report(experiment_id: str) -> str:
    s = status(experiment_id)
    lines = [
        f"EXPERIMENT {s['experiment_id']} — {s['title']}",
        f"State: {s['state']}" + (" (extended once)" if s["extended"] else ""),
        f"Window: {s['started_at'] or 'not started'} → {s['window_end'] or '-'}"
        + (f" (day {s['day']})" if s["day"] else ""),
        f"Funnel: {s['sent']} sent (need {s['min_contacts']}), {s['replied']} replied, "
        f"{s['interested']} interested, {s['claimed_paid']} claimed paid",
        f"Evidenced: {s['paid']} paid, ₹{s['revenue_inr']:.0f} ACTUAL revenue "
        f"(success at {s['success_paid_min']})",
    ]
    if s["reasons"]:
        lines.append("Reasons given: " + ", ".join(f"{k} {v}" for k, v in sorted(s["reasons"].items())))
    if s["decision"]:
        lines += ["", "Decision this forces:", s["decision"]]
    return "\n".join(lines)


def decide(experiment_id: str) -> dict:
    """Write RESULT.md once a verdict exists.  Idempotent; refuses while running."""
    s = status(experiment_id)
    if not s["decided"]:
        raise ExperimentError(f"{experiment_id} is {s['state']} — no verdict yet")
    folder = Path(s["folder"])
    body = "\n".join([
        f"# {s['experiment_id']} RESULT: {s['state']}",
        "",
        f"Measured {s['measured_at']}.",
        f"Sent {s['sent']}, replied {s['replied']}, paid {s['paid']} "
        f"(₹{s['revenue_inr']:.0f} evidenced) over {s['window_days']} days.",
        "",
        "## Decision this forces",
        s["decision"] or "(none recorded in experiment.json)",
        "",
    ])
    util.atomic_write(folder / "RESULT.md", body)
    db.log_event("aion", "experiment.decided", s["experiment_id"], s["state"])
    return {"experiment_id": s["experiment_id"], "state": s["state"],
            "result_file": str(folder / "RESULT.md"), "decision": s["decision"]}
