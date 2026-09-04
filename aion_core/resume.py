"""Checkpoint and exact-resume state.

Written after every meaningful milestone so a killed session, a compacted
context or a model switch never loses the thread.
"""
from __future__ import annotations

from . import (approvals, config, db, errors, governor, metrics, notebook, packets,
               sessions, sevaa, tasks, util)

KEYS = ["objective", "current_state", "current_task", "last_verified_success",
        "last_failure", "bottleneck", "next_action", "files_to_read"]


def checkpoint(**kw) -> dict:
    """Merge the given fields into the resume point and persist it."""
    state = load()
    for key, value in kw.items():
        if value is not None:
            state[key] = value
    counts = tasks.counts()
    nxt = tasks.next_task()
    budget = metrics.budget_status()
    state.update({
        "at": util.now(),
        "schema_version": config.SCHEMA_VERSION,
        "prompt_version": config.PROMPT_VERSION,
        "task_counts": counts,
        "open_approvals": [r["approval_id"] for r in approvals.pending()],
        "open_errors": [r["error_id"] for r in errors.open_errors(limit=10)],
        "packets": packets.stats(),
        "budget": budget,
        "highest_value_ready_task": (
            {"task_id": nxt["task_id"], "title": nxt["title"], "value": tasks.value(nxt)}
            if nxt else None),
    })
    state["bottleneck"] = _fresh_bottleneck(state.get("bottleneck", ""), nxt)
    if not state.get("next_action") and nxt is not None:
        state["next_action"] = f"work {nxt['task_id']}: {nxt['next_action'] or nxt['title']}"
    util.write_json(_path(), state)
    _render_markdown(state)
    db.set_meta("last_checkpoint", state["at"])
    db.log_event("aion", "checkpoint", state.get("current_task", ""), state.get("next_action", ""))
    return state


_TASK_REF = __import__("re").compile(r"\bTASK-[A-Z0-9]{6,}\b")


def _fresh_bottleneck(current: str, nxt) -> str:
    """A bottleneck naming a finished task is stale; recompute it."""
    if not current:
        return current
    for ref in _TASK_REF.findall(current):
        row = tasks.get(ref)
        if row is None or row["status"] in ("DONE", "CANCELLED"):
            if nxt is not None:
                return f"execution capacity on {nxt['task_id']}"
            return "empty ready queue — decompose the objective into executable tasks"
    return current


def load() -> dict:
    return util.read_json(_path(), default={}) or {}


def _path():
    return config.home() / "state" / "RESUME.json"


def _render_markdown(state: dict) -> None:
    lines = [
        "# RESUME POINT",
        "",
        f"Generated: {state.get('at')}  ·  prompt v{state.get('prompt_version')}",
        "",
        f"**Objective**: {state.get('objective', 'not set')}",
        f"**Current state**: {state.get('current_state', 'not set')}",
        f"**Current task**: {state.get('current_task', 'none')}",
        f"**Last verified success**: {state.get('last_verified_success', 'none recorded')}",
        f"**Last failure**: {state.get('last_failure', 'none recorded')}",
        f"**Current bottleneck**: {state.get('bottleneck', 'not identified')}",
        "",
        "## Exact next action",
        state.get("next_action", "not set"),
        "",
        "## Files to read next",
        state.get("files_to_read", "not set"),
        "",
        "## Queue",
        f"- Task counts: {state.get('task_counts', {})}",
        f"- Open approvals: {', '.join(state.get('open_approvals', [])) or 'none'}",
        f"- Open errors: {', '.join(state.get('open_errors', [])) or 'none'}",
        f"- Budget governor: {state.get('budget', {}).get('governor', 'unknown')}",
        "",
    ]
    util.atomic_write(config.home() / "RESUME.md", "\n".join(lines))


def boot() -> dict:
    """Startup / resume loop from directive 29 and the recovery prompt.

    Verifies state, ingests the inbox, repairs stale claims, checks approvals,
    then names the highest-value unblocked task.  It never blindly re-runs the
    previously recorded action.
    """
    steps = []
    from . import bootstrap
    created = bootstrap.ensure()
    steps.append({"step": "verify_shared_brain", "detail": f"{created} paths created/verified"})

    stored_prompt = db.get_meta("prompt_version")
    if stored_prompt != config.PROMPT_VERSION:
        db.set_meta("prompt_version", config.PROMPT_VERSION)
        steps.append({"step": "prompt_version",
                      "detail": f"{stored_prompt or 'unset'} -> {config.PROMPT_VERSION}"})
    else:
        steps.append({"step": "prompt_version", "detail": f"unchanged ({config.PROMPT_VERSION})"})

    ingested = packets.ingest_inbox()
    steps.append({"step": "process_sync_inbox", "detail": f"{len(ingested)} packet(s)",
                  "results": ingested})

    nb = notebook.sync()
    steps.append({"step": "sync_notebook",
                  "detail": f"{nb['applied']} new entr{'y' if nb['applied'] == 1 else 'ies'} applied, "
                            f"{nb['skipped_duplicates']} duplicate(s) skipped",
                  "created": nb["created"]})

    compacted = sessions.compact_old()
    if compacted:
        steps.append({"step": "compact_session_logs", "detail": f"{compacted} old log(s) compacted"})

    stale = tasks.release_stale()
    steps.append({"step": "recover_stale_claims", "detail": f"{len(stale)} released", "tasks": stale})

    pending = approvals.pending()
    steps.append({"step": "check_approvals",
                  "detail": ", ".join(r["approval_id"] for r in pending) or "none pending"})

    open_errs = errors.open_errors(limit=5)
    steps.append({"step": "check_failures", "detail": f"{len(open_errs)} unresolved"})

    health = __import__("aion_core.health", fromlist=["health"]).run_all()
    steps.append({"step": "health", "detail": "healthy" if health["healthy"]
                  else "failing: " + ", ".join(health["failing"])})

    budget = metrics.budget_status()
    shift = governor.enforce()
    steps.append({"step": "budget", "detail": budget["governor"]
                  + (f" — {shift['message']}" if shift["changed"] else "")})

    if sevaa.automation_token():
        recon = sevaa.reconcile_payments()
        steps.append({"step": "sevaa_reconcile",
                      "detail": (f"{len(recon['recorded'])} payment(s) recorded" if recon["ok"]
                                else f"unreachable: {recon['error']}")})
        synced = _sync_sevaa_approvals()
        steps.append({"step": "sevaa_approvals",
                      "detail": (f"{synced['created']} new card(s)" if synced["ok"]
                                else f"unreachable: {synced['error']}")})

    prev = load()
    nxt = tasks.next_task()
    bottleneck = identify_bottleneck(health, pending, open_errs, nxt)
    state = checkpoint(
        bottleneck=bottleneck,
        current_state=("healthy" if health["healthy"] else "degraded: " + ", ".join(health["failing"])),
        next_action=(f"work {nxt['task_id']}: {nxt['next_action'] or nxt['title']}" if nxt
                     else prev.get("next_action", "no ready task — triage the queue")),
    )
    return {"steps": steps, "resume": state, "health": health,
            "previous_next_action": prev.get("next_action")}


def _sync_sevaa_approvals() -> dict:
    """A pending SEVAA proposal approval becomes a WhatsApp card exactly once.

    Only scope_summary and the amount cross into the card text; lead_name and
    lead_company (present in the SEVAA response) are read here and discarded --
    they never reach `approvals.create`.
    """
    import json as _json
    import urllib.error as _urlerr
    try:
        rows = sevaa.list_pending_approvals()
    except sevaa.SevaaError as exc:
        return {"ok": False, "error": str(exc), "created": 0}
    except (_urlerr.URLError, _urlerr.HTTPError, OSError, ValueError, _json.JSONDecodeError) as exc:
        return {"ok": False, "error": exc.__class__.__name__, "created": 0}
    created = 0
    for row in rows:
        ref = f"{sevaa.EXTERNAL_REF_PREFIX}{row['id']}"
        if approvals.get_by_external_ref(ref) is not None:
            continue
        scope = (row.get("scope_summary") or "proposal")[:200]
        amount = row.get("amount")
        approvals.create(
            f"Approve SEVAA proposal — {scope}",
            why="a founder-gated proposal is awaiting a decision in SEVAA",
            cost=f"₹{amount}" if amount is not None else "see SEVAA console",
            max_downside="proposal terms as drafted in SEVAA; no payment is taken by approving",
            reversibility="the SEVAA decision can be revisited in the founder console",
            prepared="the proposal is already drafted and ready in SEVAA",
            resumes="the buyer-facing proposal moves forward in SEVAA",
            recommendation="REVIEW",
            external_ref=ref,
        )
        created += 1
    return {"ok": True, "created": created}


def identify_bottleneck(health, pending_approvals, open_errs, next_ready) -> str:
    """Root-bottleneck rule: name the single constraint limiting progress."""
    if not health["healthy"]:
        return f"system health: {', '.join(health['failing'])}"
    if open_errs:
        return f"{len(open_errs)} unresolved failure(s) — root-cause before adding work"
    if next_ready is None and pending_approvals:
        return (f"every remaining task waits on owner approval "
                f"({', '.join(r['approval_id'] for r in pending_approvals)})")
    if next_ready is None:
        return "empty ready queue — decompose the objective into executable tasks"
    return f"execution capacity on {next_ready['task_id']}"
