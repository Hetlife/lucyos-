"""Task-specific context packets.

A worker gets only what its task needs: the objective, the current state, the
relevant files, the recent failures and the success criteria — never the whole
repository or the whole chat history.  This is the main token-waste control.
"""
from __future__ import annotations

from . import agents, db, errors, memory, resume, security, tasks


def build(task_id: str) -> str:
    row = tasks.get(task_id)
    if row is None:
        return f"no such task {task_id}"
    r = resume.load()
    related = memory.search(row["title"], limit=5)
    recent_errs = db.connect().execute(
        "SELECT error_id, kind, message FROM errors WHERE task_id=? OR component=? "
        "ORDER BY created_at DESC LIMIT 3", (task_id, row["project"])).fetchall()
    route = agents.route(row["model_class"].lower() if row["model_class"] else "code",
                         complexity=min(5, row["priority"] + 1))
    lines = [
        f"# WORK ORDER {task_id}",
        "",
        f"TASK_ID: {task_id}",
        f"OBJECTIVE: {row['title']}",
        f"WHY IT MATTERS: {row['description'] or 'not recorded'}",
        f"PROJECT: {row['project']}",
        f"STATUS: {row['status']}   PRIORITY: {row['priority']}   VALUE: {tasks.value(row)}",
        f"ASSIGNED CLASS: {row['model_class']} (router suggests {route['model_class']}: {route['reason']})",
        "",
        "## CURRENT STATE",
        r.get("current_state", "not recorded"),
        f"Bottleneck: {r.get('bottleneck', 'not identified')}",
        "",
        "## FILES",
        row["output_location"] or "not specified",
        "",
        "## SUCCESS CRITERIA",
        row["success_criteria"] or "not recorded — define before claiming DONE",
        "",
        "## VALIDATION METHOD",
        row["validation_method"] or "run the repo test suite and record the command + result",
        "",
        "## CONSTRAINTS",
        "- Do not mark DONE without evidence (a command run, a measurement, an observation).",
        "- Never write a credential into shared state, git, logs or WhatsApp.",
        "- Tier-3 actions (spend, contracts, credentials, irreversible changes) need an approval id.",
        "- Escalate after two materially different failures instead of looping.",
        "",
        "## RELEVANT MEMORY",
    ]
    lines += [f"- {m['memory_id']} [{m['confidence']}] {m['title']}" for m in related] or ["- none"]
    lines += ["", "## RECENT FAILURES"]
    lines += [f"- {e['error_id']} ({e['kind']}) {e['message'][:120]}" for e in recent_errs] or ["- none"]
    lines += ["", "## RETURN THIS RESULT PACKET", "",
              "TASK_ID / STATUS / ACTIONS_TAKEN / FILES_CHANGED / TESTS_RUN / RESULTS / "
              "FAILURES / RISKS / ASSUMPTIONS / NEXT_RECOMMENDED_ACTION / EXACT_RESUME_POINT", ""]
    return security.redact("\n".join(lines))
