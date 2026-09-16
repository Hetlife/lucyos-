"""Task admission control (directive sections 11-13): can this task safely start now?

`evaluate()` is a pure function of a task row and a resource snapshot — it
never mutates anything, so it is cheap to call speculatively (a dry run, a
resume check) as well as for real.  `apply()` is the only function that
changes state, and only when the caller (the worker loop, gated by the
`resource_governor.enforce_admission` flag) chooses to act on the decision.

Model routing itself is untouched: `agents.route()` still decides *which*
agent/model class a kind of work needs.  This module only asks a narrower
question on top of that — does the required class have the capacity to run
right now — and never escalates a task to a class it wasn't already going to
need.
"""
from __future__ import annotations

from .. import approvals, db
from . import estimator, flags, observability

DECISIONS = ("RUN_NOW", "RUN_LOCAL", "RUN_CHEAPER_MODEL", "RUN_REDUCED_SCOPE",
             "CHECKPOINT_FIRST", "DEFER_UNTIL_RESET", "REQUIRE_OWNER_DECISION")


def _row_get(task, key, default=None):
    return task.get(key, default) if isinstance(task, dict) else task[key]


def evaluate(task, *, snap: dict | None = None) -> dict:
    """Decide what should happen to `task` right now.  Never mutates anything."""
    cls = _row_get(task, "model_class") or "B"
    task_id = _row_get(task, "task_id", "")
    size_info = estimator.estimate(task if isinstance(task, dict) else dict(task))
    reasoning = []
    snap = snap if snap is not None else observability.snapshot()

    if cls == "DET":
        return _result("RUN_NOW", ["deterministic step needs no model capacity"],
                       size_info, provider=None, provider_state=None, reset_at=None)
    if cls == "D":
        return _result("REQUIRE_OWNER_DECISION",
                       ["this action crosses an owner-authority boundary regardless of capacity"],
                       size_info, provider=None, provider_state=None, reset_at=None)

    if cls == "A":
        local = snap.get("local", {})
        if local.get("available"):
            return _result("RUN_LOCAL", ["class A routes to local model capacity"],
                           size_info, provider="local", provider_state="AVAILABLE", reset_at=None)
        reasoning.append("local model unavailable — falling back to cloud-capacity evaluation")
        cls = "B"

    provider_name = "claude"
    provider = snap.get("providers", {}).get(provider_name, {})
    pstate = provider.get("state", "UNKNOWN")
    confidence = provider.get("confidence", "UNKNOWN")
    reset_at = (provider.get("quota") or {}).get("reset_at")
    size = size_info["size"]
    reasoning.append(f"{provider_name} resource state is {pstate} (confidence {confidence})")
    reasoning.append(f"estimated task size {size} ({size_info['basis']})")

    decision = _decide(pstate, cls, size, reasoning)
    result = _result(decision, reasoning, size_info, provider=provider_name,
                     provider_state=pstate, reset_at=reset_at)
    db.log_event("resource_governor", "resource_governor.admission", task_id, decision)
    return result


def _decide(pstate: str, cls: str, size: str, reasoning: list) -> str:
    if pstate == "UNKNOWN":
        reasoning.append("telemetry unknown — proceeding without a fabricated limit")
        return "RUN_NOW"
    if pstate in ("AVAILABLE", "NORMAL"):
        return "RUN_NOW"
    if pstate == "CONSERVE":
        if cls == "C":
            reasoning.append("conserving capacity — prefer a cheaper class for this work")
            return "RUN_CHEAPER_MODEL"
        return "RUN_NOW"
    if pstate == "CONSTRAINED":
        big = size in ("LARGE", "VERY_LARGE")
        if cls == "C":
            return "CHECKPOINT_FIRST" if big else "RUN_CHEAPER_MODEL"
        return "CHECKPOINT_FIRST" if big else "RUN_REDUCED_SCOPE"
    if pstate == "CRITICAL":
        if cls == "C":
            reasoning.append("class C (irreducible strong-reasoning) work under CRITICAL "
                             "capacity needs owner sign-off")
            return "REQUIRE_OWNER_DECISION"
        return "RUN_REDUCED_SCOPE" if size in ("TINY", "SMALL") else "CHECKPOINT_FIRST"
    if pstate == "EXHAUSTED":
        return "DEFER_UNTIL_RESET"
    reasoning.append(f"unrecognised resource state {pstate!r} — treating conservatively")
    return "CHECKPOINT_FIRST"


def _result(decision, reasoning, size_info, *, provider, provider_state, reset_at) -> dict:
    return {
        "decision": decision, "reasoning": reasoning, "task_size": size_info["size"],
        "estimated_tokens": size_info["estimated_tokens"], "provider": provider,
        "provider_state": provider_state, "reset_at": reset_at,
    }


def apply(task, decision_result: dict) -> dict:
    """Act on a decision for the live worker loop.

    Returns {"proceed": bool, "class_override": str|None, "note": str|None,
    "skip": {...}|None}.  `proceed=False` means the caller must not execute
    the task this iteration; `skip` is what the caller should record instead.
    """
    task_id = _row_get(task, "task_id")
    decision = decision_result["decision"]

    if decision in ("RUN_NOW", "RUN_LOCAL"):
        return {"proceed": True, "class_override": None, "note": None, "skip": None}
    if decision == "RUN_CHEAPER_MODEL":
        return {"proceed": True, "class_override": "B", "note": "downgraded for this run: "
                + "; ".join(decision_result["reasoning"]), "skip": None}
    if decision == "RUN_REDUCED_SCOPE":
        return {"proceed": True, "class_override": None,
                "note": "reduced-scope execution requested — running as prepared; "
                        "automatic scope-trimming is not implemented yet", "skip": None}

    if decision == "REQUIRE_OWNER_DECISION":
        approval_id = approvals.create(
            f"Resume {task_id} under constrained AI capacity",
            why="; ".join(decision_result["reasoning"]),
            cost="AI capacity, not money", reversibility="fully reversible — deferred, not lost",
            prepared="the task is ready; it will resume once you approve",
            resumes="re-run resource governor admission and continue", task_id=task_id)
        return {"proceed": False, "class_override": None, "note": None,
                "skip": {"task_id": task_id, "why": f"needs owner decision: {approval_id}"}}

    # DEFER_UNTIL_RESET / CHECKPOINT_FIRST
    if not flags.flag("resource_governor.auto_defer"):
        db.log_event("resource_governor", "resource_governor.admission", task_id,
                     f"{decision} recorded but not enforced (auto_defer is off)")
        return {"proceed": True, "class_override": None,
                "note": f"would {decision.lower()} but resource_governor.auto_defer is off",
                "skip": None}

    from . import checkpoint as checkpoint_mod
    checkpoint_mod.mark_waiting_for_resource(
        task_id, resource=decision_result.get("provider") or "capacity",
        expected_reset=decision_result.get("reset_at"),
        reasoning="; ".join(decision_result["reasoning"]),
        estimated_remaining_work=f"{decision_result['task_size']} "
                                 f"(~{decision_result['estimated_tokens']} tokens)")
    return {"proceed": False, "class_override": None, "note": None,
            "skip": {"task_id": task_id, "why": f"deferred: {decision}"}}
