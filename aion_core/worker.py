"""The autonomous execution loop.

This is what runs after the expensive session ends.  It takes the highest-value
ready task, routes it to the cheapest capable executor, runs it, proves it
worked, records the evidence, and moves on — with no owner involvement and no
strong-model call.

Safety rails, in order of importance:

  * Commands are allowlisted by prefix.  A plan written by a model cannot make
    this loop run arbitrary shell; anything outside the allowlist becomes an
    approval request instead of an execution.
  * `pause` and `safe mode` stop consequential work immediately.
  * The budget governor stops paid work at its ceiling.
  * Class C work is never executed here — it is left for a strong session.
  * Class D work never executes at all; it becomes an approval card.
  * Two materially different failures escalate one class instead of looping.
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

from . import (agents, approvals, config, context, db, errors, governor, metrics,
               router, security, sessions, tasks, util)

# Prefixes a plan may execute without asking.  Everything here is reversible,
# local and inspectable.  Extend deliberately with `aion allow-command`.
DEFAULT_ALLOWED = [
    "aion ", "python3 -m unittest", "python3 -m pytest", "pytest",
    "python3 ", "git status", "git diff", "git log", "git add", "git commit",
    "ls ", "cat ", "head ", "tail ", "wc ", "grep ", "rg ", "find ", "mkdir -p ",
    "cp ", "mv ", "test ", "echo ", "sort ", "uniq ", "sed -n", "awk ",
    "ollama ", "curl -s http://localhost", "bash scripts/", "./aion ",
]
# Never runnable, even if a prefix above would otherwise match.
FORBIDDEN = ["rm -rf /", "mkfs", "dd if=", ":(){", "shutdown", "reboot",
             "chmod 777 /", "curl | sh", "| sh", "> /dev/sd", "sudo "]

TIMEOUT_S = 300
MAX_OUTPUT_CHARS = 2000


class Refused(Exception):
    """The loop declined to run something.  Not a failure — a boundary."""


def allowed_commands() -> list[str]:
    extra = db.get_meta("allowed_command_prefixes", "")
    return DEFAULT_ALLOWED + [p for p in extra.split("\n") if p.strip()]


def allow_command(prefix: str) -> None:
    current = db.get_meta("allowed_command_prefixes", "")
    entries = [p for p in current.split("\n") if p.strip()]
    if prefix not in entries:
        entries.append(prefix)
    db.set_meta("allowed_command_prefixes", "\n".join(entries))
    db.log_event("owner", "worker.allow_command", prefix)


def check_command(cmd: str) -> None:
    text = (cmd or "").strip()
    if not text:
        raise Refused("empty command")
    for bad in FORBIDDEN:
        if bad in text:
            raise Refused(f"command contains a forbidden pattern: {bad!r}")
    if not any(text.startswith(p) for p in allowed_commands()):
        raise Refused(f"command is not on the allowlist: {text.split()[0]!r}. "
                      "Approve it once with `aion allow-command '<prefix>'`.")


def run_command(cmd: str, cwd: Path | None = None) -> dict:
    """Run an allowlisted command and return its real result."""
    check_command(cmd)
    try:
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                              timeout=TIMEOUT_S, cwd=str(cwd or repo_root()))
    except subprocess.TimeoutExpired:
        return {"ok": False, "code": -1, "output": f"timed out after {TIMEOUT_S}s", "cmd": cmd}
    output = ((proc.stdout or "") + (proc.stderr or "")).strip()
    if len(output) > MAX_OUTPUT_CHARS:
        output = output[:MAX_OUTPUT_CHARS] + "\n… output truncated"
    return {"ok": proc.returncode == 0, "code": proc.returncode,
            "output": security.redact(output), "cmd": cmd}


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------- executors

def ollama_available() -> bool:
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2) as r:
            return r.status == 200
    except (urllib.error.URLError, OSError, ValueError):
        return False


def run_ollama(prompt: str, model: str | None = None) -> dict:
    """Call the local model.  Free, private, and the default for class A."""
    model = model or db.get_meta("ollama_model", "llama3.1:8b")
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request("http://localhost:11434/api/generate", data=payload,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
            body = json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError) as exc:
        return {"ok": False, "output": f"ollama unavailable: {exc}", "model": model}
    return {"ok": True, "output": security.redact(body.get("response", "").strip()),
            "model": model}


def cloud_command() -> str:
    """Template for a cheap cloud worker, e.g. 'claude -p {prompt_file}'.

    Configured once with `aion set-cloud-cmd`; kept as a command template rather
    than a hard-coded API client so the owner uses whatever CLI they already
    have authenticated, with no key handling in this codebase.
    """
    return db.get_meta("cloud_worker_cmd", "") or os.environ.get("AION_CLOUD_CMD", "")


def run_cloud(prompt: str) -> dict:
    template = cloud_command()
    if not template:
        return {"ok": False, "output": "no cloud worker configured "
                                       "(aion set-cloud-cmd '<command with {prompt_file}>')"}
    prompt_file = config.home() / "AGENTS" / "work_orders" / f"prompt-{util.new_id('WO')}.txt"
    util.atomic_write(prompt_file, prompt)
    cmd = template.replace("{prompt_file}", shlex.quote(str(prompt_file)))
    result = run_command(cmd)
    return {"ok": result["ok"], "output": result["output"], "cmd": cmd}


# ---------------------------------------------------------------- the loop

def work(max_tasks: int = 5, *, dry_run: bool = False, session_id: str | None = None) -> dict:
    """Execute up to `max_tasks` ready tasks.  Returns a factual summary."""
    summary = {"attempted": 0, "done": 0, "failed": 0, "skipped": [], "stopped": None,
               "results": []}

    if router.is_paused():
        summary["stopped"] = "paused by owner"
        return summary

    shift = governor.enforce()
    if shift["changed"]:
        summary["governor"] = shift["message"]

    if dry_run:
        # A preview changes no state, so walking the ready queue is the only
        # correct way to look ahead: next_task() would return the same task.
        for task in tasks.ready(max_tasks):
            summary["results"].append(_preview(task))
        summary["attempted"] = len(summary["results"])
        summary["stopped"] = "dry run — nothing was executed"
        return summary

    own_session = session_id is None
    if own_session and not dry_run:
        session_id = sessions.start("openclaw", model_class="DET",
                                    objective=f"autonomous execution of up to {max_tasks} tasks")

    tried: set = set()
    try:
        for _ in range(max_tasks):
            # One attempt per task per run.  A task that failed a moment ago is
            # still the highest-value READY row, so without this the loop would
            # retry it three times in a few seconds, burn every retry, and
            # escalate or block it before anything else got a turn.
            task = next((t for t in tasks.ready(50) if t["task_id"] not in tried), None)
            if task is None:
                summary["stopped"] = "no ready task" if not tried else "every ready task has had its turn this run"
                break
            tried.add(task["task_id"])

            cls = task["model_class"] or "B"
            budget = metrics.budget_status()
            # A spend ceiling stops *paid* work. Deterministic and local work is
            # free, so it keeps running — the system slows down, it does not stop.
            if (budget["day_over"] or budget["month_over"]) and cls in ("B", "C"):
                summary["skipped"].append(
                    {"task_id": task["task_id"],
                     "why": f"paid class {cls} held: budget ceiling reached "
                            f"({budget['governor']})"})
                tasks.update(task["task_id"], status="WAITING",
                             blockers=f"budget ceiling ({budget['governor']})")
                continue
            if cls == "C":
                summary["skipped"].append(
                    {"task_id": task["task_id"], "why": "class C — reserved for a strong session"})
                tasks.update(task["task_id"], status="NEEDS_REVIEW")
                continue
            if cls == "D":
                result = _owner_step(task)
                summary["results"].append(result)
                if result["status"] == "DONE":
                    summary["attempted"] += 1
                    summary["done"] += 1
                else:
                    summary["skipped"].append({"task_id": task["task_id"], "why": result["detail"]})
                continue
            if router.is_safe_mode() and cls not in ("DET",):
                summary["skipped"].append(
                    {"task_id": task["task_id"], "why": "safe mode — no external model calls"})
                tasks.update(task["task_id"], status="WAITING",
                             last_error="held by safe mode")
                continue

            summary["attempted"] += 1
            result = _execute(task, cls, dry_run=dry_run, session_id=session_id)
            summary["results"].append(result)
            if result["status"] == "DONE":
                summary["done"] += 1
            elif result["status"] in ("NEEDS_APPROVAL", "SKIPPED", "WAITING"):
                summary["skipped"].append({"task_id": result["task_id"],
                                           "why": result.get("detail", result["status"])})
            else:
                summary["failed"] += 1

        if own_session and not dry_run and session_id:
            sessions.end(session_id,
                         outcome=f"{summary['done']} done, {summary['failed']} failed, "
                                 f"{len(summary['skipped'])} skipped"
                                 + (f"; stopped: {summary['stopped']}" if summary["stopped"] else ""),
                         resume_point=_next_resume_point())
    except Exception:
        if own_session and not dry_run and session_id:
            sessions.end(session_id, outcome="loop crashed", status="FAILED",
                         resume_point="inspect `aion errors`")
        raise
    return summary


def _next_resume_point() -> str:
    nxt = tasks.next_task()
    return (f"work {nxt['task_id']}: {nxt['next_action'] or nxt['title']}" if nxt
            else "queue empty — triage or plan more work")


def _owner_step(task) -> dict:
    """A class-D step is done by the owner, not by us — but it can still finish.

    Before approval: raise the card once.  After the owner approves: the step
    is DONE only when its own validation passes (the owner really did the
    thing), otherwise it stays READY and is re-checked on the next loop.
    Without this a D step could never complete and the plan behind it stalled
    forever on a card the owner had already answered.
    """
    task_id = task["task_id"]
    approval_id = task["approval_id"]
    row = approvals.get(approval_id) if approval_id else None
    if row is None or row["status"] == approvals.PENDING:
        approval_id = _raise_approval(task)
        return {"task_id": task_id, "status": "NEEDS_APPROVAL", "approval": approval_id,
                "detail": "owner authority required"}
    if row["status"] != approvals.APPROVED:
        return {"task_id": task_id, "status": "SKIPPED",
                "detail": f"{approval_id} was {row['status'].lower()}"}
    checked = _validate(task, {"output": f"{approval_id} approved by {row['decided_by']}"})
    if not checked["ok"]:
        tasks.update(task_id, last_error=f"approved but not yet verifiable: {checked['detail'][:300]}")
        return {"task_id": task_id, "status": "WAITING",
                "detail": f"{approval_id} approved; waiting for proof — {checked['detail'][:200]}"}
    evidence = f"owner step: {approval_id} approved by {row['decided_by']}; {checked['detail']}"
    tasks.complete(task_id, evidence[:900], next_action="")
    return {"task_id": task_id, "status": "DONE", "class": "D", "evidence": evidence[:200]}


def _raise_approval(task) -> str:
    if task["approval_id"]:
        return task["approval_id"]
    if (task["kind"] or "") == "triage":
        return approvals.create(
            f"Triage: {task['title']}",
            why="free text captured from a message; only you can say whether it is work",
            cost="none", reversibility="fully — approving only makes it a READY task",
            prepared="nothing is executed until you approve",
            resumes="the note becomes a READY task for decomposition",
            task_id=task["task_id"])
    return approvals.create(
        task["title"], why="the step crosses an owner authority boundary",
        cost="see the task description", reversibility="unknown",
        prepared="everything up to the boundary is ready",
        resumes=task["next_action"] or "execute the prepared step",
        task_id=task["task_id"])


def _preview(task) -> dict:
    """What would happen to this task, without touching anything."""
    cls = task["model_class"] or "B"
    route = agents.route(task["kind"] or "code", complexity=min(5, task["priority"] + 1))
    if cls == "C":
        action = "left for a strong session"
    elif cls == "D":
        action = "raised as an owner approval"
    elif task["exec_command"]:
        try:
            check_command(task["exec_command"])
            action = f"run `{task['exec_command']}`"
        except Refused as exc:
            action = f"BLOCKED — {exc}"
    elif cls == "A":
        action = ("prompt the local model" if ollama_available()
                  else "no local model — would fall through to the cloud worker")
    else:
        action = ("prompt the cloud worker" if cloud_command()
                  else "no cloud worker configured — would save a work order instead")
    return {"task_id": task["task_id"], "status": "DRY_RUN", "class": cls,
            "agent": route["agent_id"], "title": task["title"], "would": action,
            "validation": task["validation_command"] or task["output_location"]
                          or "output must be non-empty"}


def _execute(task, cls: str, *, dry_run: bool, session_id: str | None) -> dict:
    task_id = task["task_id"]
    route = agents.route(task["kind"] or "code", complexity=min(5, task["priority"] + 1))
    agent_id = route["agent_id"] or "openclaw"

    if not tasks.claim(task_id, agent_id):
        return {"task_id": task_id, "status": "SKIPPED", "detail": "claimed by another worker"}
    tasks.update(task_id, status="RUNNING", started_at=util.now())
    if session_id:
        sessions.log(session_id, "action", f"{task_id} [{cls}] {task['title']}")

    try:
        produced = _do_work(task, cls)
    except Refused as exc:
        # Not a failure: a boundary. Ask instead of forcing.
        approval_id = approvals.create(
            f"Run: {task['exec_command'] or task['title']}",
            why=str(exc), cost="none directly", reversibility="depends on the command",
            prepared="the command is prepared and will run unchanged once allowed",
            resumes="execute the command", task_id=task_id)
        if session_id:
            sessions.log(session_id, "approval", f"{task_id} needs {approval_id}: {exc}")
        return {"task_id": task_id, "status": "NEEDS_APPROVAL", "approval": approval_id,
                "detail": str(exc)}

    if not produced["ok"]:
        if produced.get("unavailable"):
            # Retrying cannot help until the machine gains an executor, so this
            # waits without burning a retry — and the loop moves to other work.
            tasks.update(task_id, status="WAITING", owner_agent=None,
                         blockers=f"no {cls}-class executor on this machine",
                         last_error=produced["output"][:400])
            if session_id:
                sessions.log(session_id, "note", f"{task_id} waiting: no {cls} executor")
            return {"task_id": task_id, "status": "WAITING", "class": cls,
                    "detail": produced["output"][:300]}
        return _fail(task_id, cls, produced["output"], session_id)

    checked = _validate(task, produced)
    if not checked["ok"]:
        return _fail(task_id, cls, f"validation failed: {checked['detail']}", session_id)

    evidence = f"{produced.get('how', cls)}: {checked['detail']}"
    tasks.complete(task_id, evidence[:900], next_action="")
    agents.record_run(agent_id, success=True)
    metrics.record_usage(produced.get("model", agent_id), cls, task_id=task_id,
                         cost_inr=produced.get("cost_inr", 0.0),
                         note=task["title"][:100])
    if session_id:
        sessions.log(session_id, "result", f"{task_id} DONE — {checked['detail'][:150]}")
    return {"task_id": task_id, "status": "DONE", "class": cls, "evidence": evidence[:200]}


def _do_work(task, cls: str) -> dict:
    """Deterministic steps run their command; model steps run their prompt."""
    if task["exec_command"]:
        result = run_command(task["exec_command"])
        return {"ok": result["ok"], "output": result["output"],
                "how": f"ran `{result['cmd']}`", "model": "shell"}
    if cls == "DET":
        return {"ok": False, "output": "a DET step has no exec_command — the plan is incomplete"}

    prompt = context.build(task["task_id"])
    if task["description"] and "PROMPT FOR THE EXECUTING MODEL:" in task["description"]:
        prompt = task["description"].split("PROMPT FOR THE EXECUTING MODEL:", 1)[1].strip() \
                 + "\n\n---\n" + prompt

    if cls == "A" and ollama_available():
        out = run_ollama(prompt)
        return {"ok": out["ok"] and bool(out["output"]), "output": out["output"],
                "how": f"local model {out.get('model')}", "model": out.get("model", "ollama")}
    out = run_cloud(prompt)
    if not out["ok"]:
        # No executor available: keep the prepared work order and say so plainly.
        wo = config.home() / "AGENTS" / "work_orders" / f"{task['task_id']}.md"
        util.atomic_write(wo, prompt)
        return {"ok": False, "unavailable": True,
                "output": f"no {cls}-class executor available ({out['output']}). "
                          f"Work order saved to {wo} for a worker session."}
    return {"ok": True, "output": out["output"], "how": "cloud worker", "model": "cloud"}


def _validate(task, produced: dict) -> dict:
    """A step is only DONE if something independent says so."""
    if task["validation_command"]:
        result = run_command(task["validation_command"])
        return {"ok": result["ok"],
                "detail": f"`{result['cmd']}` exited {result['code']}; "
                          f"{result['output'][:400] or 'no output'}"}
    if task["output_location"]:
        p = Path(task["output_location"])
        if not p.is_absolute():
            p = repo_root() / p
        exists = p.exists() and p.stat().st_size > 0
        return {"ok": exists,
                "detail": f"{p} {'exists' if exists else 'was not written'}"}
    text = (produced.get("output") or "").strip()
    return {"ok": bool(text),
            "detail": f"produced {len(text)} characters of output: {text[:300]}"}


def _fail(task_id: str, cls: str, message: str, session_id: str | None) -> dict:
    error_id = errors.record("worker", message[:400], task_id=task_id)
    status = tasks.fail(task_id, message[:400])
    row = tasks.get(task_id)
    escalated = None
    # Two materially different failures mean the class is wrong, not the task.
    if row["retry_count"] >= 2 and cls in ("DET", "A", "B"):
        escalated = agents.escalate(cls, f"{row['retry_count']} failures on {task_id}")
        tasks.update(task_id, model_class=escalated["model_class"])
    if session_id:
        sessions.log(session_id, "failure", f"{task_id} {status}: {message[:150]}")
    return {"task_id": task_id, "status": status, "error": error_id,
            "escalated_to": escalated["model_class"] if escalated else None,
            "detail": message[:300]}


def capability_report() -> dict:
    """What this machine can actually execute right now — measured."""
    return {
        "ollama": ollama_available(),
        "ollama_model": db.get_meta("ollama_model", "llama3.1:8b"),
        "cloud_worker": bool(cloud_command()),
        "cloud_worker_cmd": cloud_command() or "not configured",
        "allowlisted_prefixes": len(allowed_commands()),
        "paused": router.is_paused(),
        "safe_mode": router.is_safe_mode(),
        "governor": metrics.budget_status()["governor"],
    }
