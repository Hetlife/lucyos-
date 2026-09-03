"""PLAN ingestion — the handoff from expensive thinking to cheap doing.

The strong model's real output is not code, it is a *task graph*: a set of
steps, each already routed to the cheapest class that can do it, each carrying
the command that performs it, the command that proves it worked, and the
criterion a human would use to judge it.

Once a plan lands here, `aion work` executes it without further expensive
reasoning.  That is the whole economic point: pay once for the thinking, then
run the doing on local and cheap models forever.

Format: JSON, because a machine executes it.  See SCHEMAS/plan.schema.json.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import agents, config, db, memory, security, tasks, util

REQUIRED_STEP_FIELDS = ("id", "title", "kind")
VALID_CLASSES = ("DET", "A", "B", "C", "D")


class PlanError(Exception):
    pass


TEMPLATE = {
    "plan_id": "PLAN-<short-name>",
    "objective": "the end state this plan reaches, in one sentence",
    "bottleneck": "the single constraint this plan removes",
    "success": "how anyone can tell the whole plan worked",
    "steps": [
        {
            "id": "s1",
            "title": "one concrete step",
            "kind": "classify|extract|format|summarize|code|research|file_write|test_run|git|spend",
            "why": "why this step exists",
            "model_class": "DET|A|B|C|D — omit to let the router decide",
            "depends_on": ["ids of steps that must finish first"],
            "prompt": "for A/B steps: the exact instruction a cheap model executes",
            "exec_command": "for DET steps: the command that performs the work",
            "validation_command": "a command that exits 0 only if the step really worked",
            "success_criteria": "what a human would check",
            "impact": 3, "cost": 1, "risk": 1,
            "output_location": "path the step writes to",
        }
    ],
}


def validate(doc: dict) -> list[str]:
    """Return a list of problems.  Empty means the plan is executable."""
    problems = []
    if not isinstance(doc, dict):
        return ["plan must be a JSON object"]
    if not doc.get("objective"):
        problems.append("missing 'objective'")
    steps = doc.get("steps")
    if not isinstance(steps, list) or not steps:
        return problems + ["'steps' must be a non-empty list"]

    ids = set()
    for i, step in enumerate(steps):
        where = f"step {i} ({step.get('id', 'no id')})"
        if not isinstance(step, dict):
            problems.append(f"{where}: not an object")
            continue
        for field in REQUIRED_STEP_FIELDS:
            if not step.get(field):
                problems.append(f"{where}: missing '{field}'")
        sid = step.get("id")
        if sid in ids:
            problems.append(f"{where}: duplicate id '{sid}'")
        ids.add(sid)
        cls = step.get("model_class")
        if cls and cls not in VALID_CLASSES:
            problems.append(f"{where}: model_class '{cls}' is not one of {VALID_CLASSES}")
        if not step.get("validation_command") and not step.get("success_criteria"):
            problems.append(f"{where}: needs a validation_command or a success_criteria — "
                            "a step with no way to check it can never be marked DONE")
        if cls == "DET" and not step.get("exec_command"):
            problems.append(f"{where}: a DET step must carry an exec_command")
        if cls in ("A", "B") and not step.get("prompt"):
            problems.append(f"{where}: an {cls} step must carry the prompt the cheap model runs")
    for step in steps:
        for dep in step.get("depends_on") or []:
            if dep not in ids:
                problems.append(f"step {step.get('id')}: depends on unknown step '{dep}'")
    problems.extend(_cycles(steps))
    return problems


def _cycles(steps: list) -> list[str]:
    graph = {s.get("id"): list(s.get("depends_on") or []) for s in steps if isinstance(s, dict)}
    state: dict = {}

    def visit(node, trail):
        if state.get(node) == "done":
            return []
        if state.get(node) == "open":
            return [f"dependency cycle: {' -> '.join(trail + [node])}"]
        state[node] = "open"
        found = []
        for dep in graph.get(node, []):
            found += visit(dep, trail + [node])
        state[node] = "done"
        return found

    out = []
    for node in graph:
        out += visit(node, [])
    return sorted(set(out))


def apply(doc: dict, *, source: str = "strong-model plan") -> dict:
    """Turn a validated plan into real queued tasks.  Idempotent per plan_id."""
    problems = validate(doc)
    if problems:
        raise PlanError("plan rejected:\n  - " + "\n  - ".join(problems))

    plan_id = doc.get("plan_id") or f"PLAN-{util.sha256_text(json.dumps(doc, sort_keys=True))[:8].upper()}"
    if db.seen(f"plan:{plan_id}", "plan_apply"):
        existing = db.connect().execute(
            "SELECT task_id FROM tasks WHERE plan_id=?", (plan_id,)).fetchall()
        return {"plan_id": plan_id, "status": "ALREADY_APPLIED",
                "tasks": [r["task_id"] for r in existing]}

    memory.decide(f"plan {plan_id}", doc["objective"],
                  rationale=doc.get("bottleneck", ""), evidence=source,
                  confidence="SUPPORTED_FACT", made_by="strong model")

    id_map: dict[str, str] = {}
    order = _topological(doc["steps"])
    for step in order:
        cls = step.get("model_class") or agents.route(
            step["kind"], complexity=int(step.get("complexity", 2)))["model_class"]
        deps = ",".join(id_map[d] for d in (step.get("depends_on") or []) if d in id_map)
        description = security.redact(step.get("why", ""))
        if step.get("prompt"):
            description += ("\n\nPROMPT FOR THE EXECUTING MODEL:\n"
                            + security.redact(step["prompt"]))
        task_id = tasks.create(
            step["title"],
            project=doc.get("project", "default"),
            description=description,
            kind=step["kind"],
            model_class=cls,
            dependencies=deps,
            impact=float(step.get("impact", 3)),
            cost=float(step.get("cost", 1)),
            risk=float(step.get("risk", 1)),
            priority=int(step.get("priority", 2)),
            success_criteria=step.get("success_criteria", ""),
            validation_method=step.get("validation_command") or step.get("success_criteria", ""),
            exec_command=step.get("exec_command", ""),
            validation_command=step.get("validation_command", ""),
            output_location=step.get("output_location", ""),
            next_action=step.get("exec_command") or step.get("prompt", "")[:200],
            plan_id=plan_id,
        )
        id_map[step["id"]] = task_id

    _write_plan_file(plan_id, doc, id_map)
    db.log_event("aion", "plan.apply", plan_id, f"{len(id_map)} steps queued")
    return {"plan_id": plan_id, "status": "APPLIED", "tasks": list(id_map.values()),
            "steps": len(id_map)}


def _topological(steps: list) -> list:
    """Create parents before children so dependency ids resolve."""
    by_id = {s["id"]: s for s in steps}
    done, order = set(), []

    def visit(sid):
        if sid in done or sid not in by_id:
            return
        for dep in by_id[sid].get("depends_on") or []:
            visit(dep)
        done.add(sid)
        order.append(by_id[sid])

    for s in steps:
        visit(s["id"])
    return order


def _write_plan_file(plan_id: str, doc: dict, id_map: dict) -> Path:
    d = config.home() / "PROJECTS" / "plans"
    d.mkdir(parents=True, exist_ok=True)
    record = {"plan_id": plan_id, "applied_at": util.now(), "objective": doc["objective"],
              "bottleneck": doc.get("bottleneck", ""), "success": doc.get("success", ""),
              "step_to_task": id_map, "plan": doc}
    return util.write_json(d / f"{plan_id}.json", record)


def load(path: Path) -> dict:
    text = Path(path).read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise PlanError(f"{path} is not valid JSON: {exc}") from exc


def write_schema() -> Path:
    """Emit the template a strong model fills in."""
    return util.write_json(config.home() / "SCHEMAS" / "plan.template.json", TEMPLATE)


def status(plan_id: str) -> dict:
    rows = db.connect().execute(
        "SELECT status, COUNT(*) c FROM tasks WHERE plan_id=? GROUP BY status",
        (plan_id,)).fetchall()
    counts = {r["status"]: r["c"] for r in rows}
    total = sum(counts.values())
    return {"plan_id": plan_id, "steps": total, "counts": counts,
            "complete": total > 0 and counts.get("DONE", 0) == total}
