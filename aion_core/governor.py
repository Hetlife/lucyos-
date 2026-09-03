"""Automatic downshift.

The owner should not have to watch a budget and remember to say "use a cheaper
model now".  As spend crosses each threshold this demotes queued work to the
cheapest class that can still do it, records why, and — only at the hard stop —
tells the owner.

Nothing here ever *upgrades* a task: cost can only fall automatically.  Moving
work back up is a deliberate act (`aion task-update --status`), because it
spends money.
"""
from __future__ import annotations

from . import db, memory, metrics, tasks, util

# governor state -> what class C work becomes, and whether B work drops to A.
POLICY = {
    "NORMAL": {"demote_c": None, "demote_b": False},
    "ARCHITECTURE-DONE": {"demote_c": None, "demote_b": False},
    "SHIFT-DOWN": {"demote_c": "B", "demote_b": False},
    "RESERVE": {"demote_c": "B", "demote_b": True},
    "CRITICAL-ONLY": {"demote_c": "B", "demote_b": True},
    "HANDOFF": {"demote_c": "B", "demote_b": True},
    "STOP": {"demote_c": "HOLD", "demote_b": True},
}

# Kinds that genuinely cannot be done by a cheap model.  These are held for a
# strong session rather than silently degraded into a worse answer.
IRREDUCIBLE = {"security_review", "finance_reason", "architecture"}


def state() -> str:
    return metrics.budget_status()["governor"].split(" ")[0]


def enforce(*, announce: bool = True) -> dict:
    """Apply the current policy to the queue.  Safe to run on every loop."""
    now_state = state()
    policy = POLICY.get(now_state, POLICY["NORMAL"])
    previous = db.get_meta("governor_state", "NORMAL")
    result = {"state": now_state, "previous": previous, "demoted": [], "held": [],
              "changed": now_state != previous, "message": ""}

    if policy["demote_c"]:
        for row in tasks.by_status("READY") + tasks.by_status("TRIAGE"):
            if row["model_class"] != "C":
                continue
            if policy["demote_c"] == "HOLD" or (row["kind"] or "") in IRREDUCIBLE:
                tasks.update(row["task_id"], status="NEEDS_REVIEW",
                             last_error=f"held: budget governor is {now_state}")
                result["held"].append(row["task_id"])
            else:
                tasks.update(row["task_id"], model_class=policy["demote_c"])
                result["demoted"].append(f"{row['task_id']} C->{policy['demote_c']}")

    if policy["demote_b"]:
        for row in tasks.by_status("READY"):
            if row["model_class"] == "B" and (row["kind"] or "") not in IRREDUCIBLE:
                tasks.update(row["task_id"], model_class="A")
                result["demoted"].append(f"{row['task_id']} B->A")

    if result["changed"]:
        db.set_meta("governor_state", now_state)
        b = metrics.budget_status()
        memory.decide(
            "budget governor", f"moved {previous} -> {now_state}",
            rationale=f"strong-model spend is INR {b['strong_model_spend_inr']} of "
                      f"{b['strong_model_cap_inr']} ({b['strong_model_pct']}%)",
            evidence="aion usage records", confidence="VERIFIED_FACT", made_by="governor")
        db.log_event("governor", "downshift", now_state,
                     f"{len(result['demoted'])} demoted, {len(result['held'])} held")
        result["message"] = _message(now_state, result)
        if announce and now_state in ("STOP", "HANDOFF"):
            db.set_meta("owner_alert", result["message"])
    return result


def _message(now_state: str, result: dict) -> str:
    b = metrics.budget_status()
    head = (f"Budget governor is now {now_state} — strong-model spend is "
            f"INR {b['strong_model_spend_inr']} of {b['strong_model_cap_inr']} "
            f"({b['strong_model_pct']}%).")
    if now_state == "STOP":
        return (head + f" No further strong-model work will run. "
                f"{len(result['held'])} task(s) are held for you to authorise more budget, "
                f"or to re-scope. Everything cheaper keeps running.")
    if now_state == "HANDOFF":
        return head + " Discretionary strong-model use has stopped; the session should hand off."
    moved = ", ".join(result["demoted"][:6]) or "nothing needed moving"
    return head + f" Automatically moved work down: {moved}."


def pending_alert() -> str | None:
    """One-shot alert for the owner, cleared once delivered."""
    alert = db.get_meta("owner_alert", "")
    if alert:
        db.set_meta("owner_alert", "")
    return alert or None
