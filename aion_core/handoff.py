"""Automatic handoff from the strong session to the unattended Sonnet loop.

The owner should never have to notice that a budget ran out and remember to
switch models.  When the governor reaches HANDOFF or STOP this writes the
continuation prompt, points routing at the cheaper worker, and leaves an alert
in `status`.

The handoff is deliberately *not* silent: switching who does the work is a
material change, so it is recorded as a decision with the spend that caused it.
"""
from __future__ import annotations

from pathlib import Path

from . import agents, approvals, config, db, metrics, resume, security, tasks, util

PROMPT_NAME = "SONNET_START_PROMPT.txt"


def pack_dir() -> Path:
    d = config.home() / "FABLE"
    d.mkdir(parents=True, exist_ok=True)
    return d


def prompt_path() -> Path:
    return pack_dir() / PROMPT_NAME


def build_prompt() -> Path:
    """The continuation prompt for the unattended session."""
    r = resume.load()
    b = metrics.budget_status()
    home, repo = config.home(), Path(__file__).resolve().parent.parent
    ready = tasks.ready(8)
    held = [t for t in tasks.by_status("NEEDS_REVIEW")]

    lines = [
        "YOU ARE THE UNATTENDED EXECUTION SESSION FOR AN ALREADY-BUILT AION SYSTEM.",
        "",
        "The strong-reasoning session has finished or run out of budget. The thinking is",
        "done and written down. Your job is to execute what it planned, cheaply, and to",
        "stop rather than improvise when something genuinely needs more intelligence.",
        "",
        "READ ONLY THESE, IN THIS ORDER:",
        f"1. {home}/FABLE/FABLE_HANDOFF.md      — what the strong session actually did",
        f"2. {home}/RESUME.md                    — the exact resume point",
        f"3. {home}/FABLE/FABLE_TASK_QUEUE.md    — ranked work",
        "Then run `aion boot`. Do not scan the repository.",
        "",
        "HOW YOU WORK",
        "  aion boot          # startup, ingest, recover, name the bottleneck",
        "  aion work --max 10 # execute the queue: run, validate, record evidence",
        "  aion status        # confirm the picture matches reality",
        "Repeat. The loop routes each task to the cheapest executor that can do it and",
        "refuses to mark anything DONE without evidence.",
        "",
        "WHAT YOU DO NOT DO",
        "- Do not re-plan. If a task has no executable step, it was not decomposed;",
        "  mark it NEEDS_REVIEW and move on rather than inventing an approach.",
        "- Do not touch class C work. It is reserved for a strong session.",
        "- Do not spend money or make binding commitments. Those become approval cards:",
        "  `aion approval-add` holds the one action and everything else keeps running.",
        "- Do not write a credential into state, git, logs or WhatsApp.",
        "- Do not widen scope because you have capacity. Finish the queue as planned.",
        "",
        f"BUDGET AT HANDOFF: strong-model spend was INR {b['strong_model_spend_inr']} of "
        f"INR {b['strong_model_cap_inr']} ({b['strong_model_pct']}%); governor {b['governor']}.",
        "You are the cheap tier. Record your own usage with",
        "`aion usage claude-sonnet-5 B --cost <INR> --task-id <TASK>`.",
        "",
        f"CURRENT BOTTLENECK: {r.get('bottleneck', 'not identified')}",
        f"EXACT NEXT ACTION: {r.get('next_action', 'run `aion boot`')}",
        "",
        "QUEUE AT HANDOFF:",
    ]
    lines += [f"  {t['task_id']} [class {t['model_class']}] {t['title']}" for t in ready] or \
             ["  (nothing ready — run `aion boot` and check `aion blockers`)"]
    if held:
        lines += ["", "HELD FOR A STRONG SESSION — leave these alone:"]
        lines += [f"  {t['task_id']} {t['title']}" for t in held[:8]]
    if approvals.pending():
        lines += ["", "WAITING ON THE OWNER — do not work around these:"]
        lines += [f"  {a['approval_id']} {a['action']}" for a in approvals.pending()]
    lines += [
        "",
        "WHEN TO STOP AND ASK",
        "Two materially different failures on the same task, an architectural choice, a",
        "security question, or anything touching money. Say so plainly and stop; the owner",
        "would rather open a strong session than receive a confident guess.",
        "",
        "FINISH BY updating the session log and leaving an exact resume point:",
        "  aion checkpoint --current-task <ID> --next-action '<the real next step>'",
        "",
        f"REPOSITORY: {repo}",
        f"SHARED BRAIN: {home}",
        "START NOW BY RUNNING `aion boot`.",
        "",
    ]
    return util.atomic_write(prompt_path(), security.redact("\n".join(lines)))


def execute(reason: str, *, to_agent: str = "cloud-sonnet") -> dict:
    """Switch the automated session to the cheaper worker.  Idempotent."""
    already = db.get_meta("handoff_done", "")
    path = build_prompt()
    if already:
        return {"status": "ALREADY_HANDED_OFF", "at": already, "prompt": str(path)}

    agent = agents.get(to_agent)
    if agent is None:
        agents.seed_defaults()
        agent = agents.get(to_agent)
    if agent is not None:
        agents.set_preferred("B", to_agent)

    b = metrics.budget_status()
    from . import memory
    memory.decide(
        "model handoff", f"unattended execution moved to {to_agent}",
        rationale=reason,
        evidence=f"strong-model spend INR {b['strong_model_spend_inr']} of "
                 f"{b['strong_model_cap_inr']} ({b['strong_model_pct']}%)",
        confidence="VERIFIED_FACT", made_by="governor")
    db.set_meta("handoff_done", util.now())
    db.set_meta("owner_alert",
                f"Switched to {to_agent} for unattended work: {reason} "
                f"Strong-model spend stopped at INR {b['strong_model_spend_inr']}. "
                f"Continuation prompt: {path}")
    db.log_event("governor", "handoff", to_agent, reason)
    return {"status": "HANDED_OFF", "to": to_agent, "prompt": str(path), "reason": reason,
            "spend_inr": b["strong_model_spend_inr"]}


def status() -> dict:
    return {"handed_off_at": db.get_meta("handoff_done", "") or None,
            "preferred_class_b": agents.preferred("B") or "highest reliability",
            "prompt": str(prompt_path()) if prompt_path().exists() else "not written yet"}
