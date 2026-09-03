"""Fable launch pack: prepare everything cheaply, then hand a strong model one
compact, high-value job.

Nothing here spends money.  It assembles the context, the budget governor and
the readiness test so that when the owner does add credits, the expensive
session starts already knowing the machine.
"""
from __future__ import annotations

from pathlib import Path

from . import (agents, approvals, config, db, errors, health, metrics, packets,
               resume, security, tasks, util)

PACK = "FABLE"
BUDGET_CAP_INR = 2000.0
STAGED_FIRST_TOPUP_INR = 750.0


def pack_dir() -> Path:
    d = config.home() / PACK
    d.mkdir(parents=True, exist_ok=True)
    return d


def budget() -> dict:
    b = metrics.budget_status()
    used = b["strong_model_spend_inr"]
    return {
        "currency": "INR",
        "maximum_cumulative_authorization": BUDGET_CAP_INR,
        "used": used,
        "remaining": round(BUDGET_CAP_INR - used, 2),
        "percent_used": b["strong_model_pct"],
        "governor": b["governor"],
        "recommended_first_topup": STAGED_FIRST_TOPUP_INR,
        "thresholds": {
            "25": "architecture and persistent state established",
            "50": "shift routine execution down to local/cheap models",
            "70": "reserve strong model for unresolved high-value problems",
            "85": "critical integration, debugging and review only",
            "95": "stop discretionary use, consolidate and hand off",
            "100": "no further strong-model use without new owner authorization",
        },
        "updated_at": util.now(),
    }


def readiness() -> dict:
    """Measured readiness.  Every field comes from a real check."""
    h = health.run_all(deep=True)
    checks = {c["name"]: c for c in h["checks"]}
    r = resume.load()
    ready_tasks = tasks.ready(50)
    strong_tasks = [t for t in ready_tasks if t["model_class"] == "C"]
    scan = security.scan_paths(Path(__file__).resolve().parent.parent)
    pack_files = sorted(p.name for p in pack_dir().glob("*"))

    def state(ok: bool, partial: bool = False) -> str:
        return "READY" if ok else ("PARTIAL" if partial else "NOT READY")

    ollama = checks.get("ollama", {})
    return {
        "environment": state(checks.get("disk", {}).get("ok") and checks.get("database", {}).get("ok")),
        "openclaw": state(checks.get("shared_brain", {}).get("ok")),
        "repository": state(checks.get("git", {}).get("ok")),
        "backup": state(checks.get("backup", {}).get("ok")),
        "shared_brain": state(checks.get("shared_brain", {}).get("ok")),
        "task_queue": state(bool(ready_tasks)),
        "checkpoint": state(bool(r.get("at"))),
        "resume": state(bool(r.get("next_action"))),
        "ollama": "READY" if ollama.get("ok") and "not installed" not in ollama.get("detail", "")
                  else "NOT REQUIRED (falls back to cheap cloud)",
        "fable_context": state(len(pack_files) >= 12),
        "budget_governor": state(bool(db.get_meta("build_budget_cap_inr"))),
        "security": "PASS" if not scan else f"ISSUES ({len(scan)} findings)",
        "critical_blockers": [f"{t['task_id']}: {t['title']}" for t in tasks.blocked()
                              if t["status"] == "BLOCKED"],
        "pending_approvals": [a["approval_id"] for a in approvals.pending()],
        "strong_model_tasks_queued": [f"{t['task_id']}: {t['title']}" for t in strong_tasks],
        "bottleneck": r.get("bottleneck", "not identified"),
        "pack_files": pack_files,
        "measured_at": util.now(),
    }


def is_ready(rd: dict | None = None) -> tuple[bool, list[str]]:
    rd = rd or readiness()
    gaps = []
    for key in ("environment", "openclaw", "repository", "shared_brain", "task_queue",
                "checkpoint", "resume", "fable_context", "budget_governor"):
        if rd[key] != "READY":
            gaps.append(f"{key}={rd[key]}")
    if rd["security"] != "PASS":
        gaps.append(f"security={rd['security']}")
    if not rd["strong_model_tasks_queued"]:
        gaps.append("no class-C task queued — a strong model has no high-value job yet")
    return (not gaps), gaps


def readiness_report() -> str:
    rd = readiness()
    ok, gaps = is_ready(rd)
    lines = ["FABLE READY" if ok else "NOT YET FABLE READY", ""]
    for label, key in [("Environment", "environment"), ("OpenClaw", "openclaw"),
                       ("Repository", "repository"), ("Backup", "backup"),
                       ("Shared Brain", "shared_brain"), ("Task Queue", "task_queue"),
                       ("Checkpoint", "checkpoint"), ("Resume", "resume"),
                       ("Ollama", "ollama"), ("Fable Context", "fable_context"),
                       ("Budget Governor", "budget_governor"), ("Security", "security")]:
        lines.append(f"{label}: {rd[key]}")
    lines.append("Critical Blockers: " + (", ".join(rd["critical_blockers"]) or "none"))
    lines.append("")
    if not ok:
        lines += ["Remaining gaps before recommending credits:"] + [f"- {g}" for g in gaps]
        return "\n".join(lines)
    b = budget()
    lines += [
        "WHY FABLE IS NOW WORTH USING:",
        f"Current bottleneck: {rd['bottleneck']}",
        "Queued strong-model work:",
    ] + [f"- {t}" for t in rd["strong_model_tasks_queued"]] + [
        "",
        f"RECOMMENDED INITIAL CREDIT: INR {b['recommended_first_topup']:.0f}",
        f"MAXIMUM CUMULATIVE AUTHORIZATION: INR {b['maximum_cumulative_authorization']:.0f}",
        f"ALREADY USED: INR {b['used']:.0f}  ·  REMAINING: INR {b['remaining']:.0f}",
        "",
        "EXPECTED FABLE ROLE:",
        "Architecture, hard debugging, security and economic reasoning, and decomposition of",
        "high-value work into work orders that local and cheap models execute afterwards.",
    ]
    return "\n".join(lines)


def build_pack() -> list[str]:
    """Write the whole launch pack.  Idempotent; safe to re-run any time."""
    d = pack_dir()
    written = []
    files = {
        "README.md": _readme(),
        "FABLE_MASTER_PROMPT.md": _master_prompt(),
        "FABLE_START_PROMPT.txt": _start_prompt(),
        "FABLE_CONTEXT.md": _context(),
        "FABLE_TASK_QUEUE.md": _task_queue(),
        "FABLE_DECISIONS.md": _decisions(),
        "FABLE_FILES_INDEX.md": _files_index(),
        "FABLE_COMPLETION_CRITERIA.md": _completion_criteria(),
        "FABLE_HANDOFF.md": _handoff(),
        "FABLE_RESUME.md": _resume_doc(),
        "FABLE_DO_NOT_WASTE_TOKENS.md": _no_waste(),
    }
    for name, body in files.items():
        util.atomic_write(d / name, security.redact(body))
        written.append(str(d / name))
    util.write_json(d / "FABLE_BUDGET.json", budget())
    written.append(str(d / "FABLE_BUDGET.json"))
    log = d / "FABLE_SESSION_LOG.md"
    if not log.exists():
        util.atomic_write(log, "# FABLE SESSION LOG\n\n"
                               "| Started | Ended | Tokens in/out | INR | Objective | Outcome |\n"
                               "|---|---|---|---|---|---|\n")
    written.append(str(log))
    util.write_json(d / "FABLE_READINESS.json", readiness())
    written.append(str(d / "FABLE_READINESS.json"))
    return written


def _readme() -> str:
    return f"""# FABLE launch pack

Generated {util.now()} by `aion fable-pack`. Regenerate any time; nothing here
is hand-maintained.

| File | Use |
|---|---|
| `FABLE_START_PROMPT.txt` | The exact text to paste into a new strong-model session. |
| `FABLE_MASTER_PROMPT.md` | Standing rules for the session (hierarchy, autonomy, approvals). |
| `FABLE_CONTEXT.md` | Compact machine + project reality. Read instead of scanning the repo. |
| `FABLE_TASK_QUEUE.md` | Ranked work, split into strong-model vs delegate-down. |
| `FABLE_BUDGET.json` | Cumulative authorization, spend so far, governor thresholds. |
| `FABLE_DECISIONS.md` | Decisions already made — do not relitigate. |
| `FABLE_FILES_INDEX.md` | Which files to read first and which to ignore. |
| `FABLE_COMPLETION_CRITERIA.md` | What DONE means for this session. |
| `FABLE_HANDOFF.md` | The packet the session must leave behind. |
| `FABLE_RESUME.md` | Exact resume point if the session dies. |
| `FABLE_SESSION_LOG.md` | Append one row per session: spend and outcome. |
| `FABLE_DO_NOT_WASTE_TOKENS.md` | Concrete waste rules for this repository. |
"""


def _master_prompt() -> str:
    return f"""# FABLE MASTER PROMPT

Prompt version {config.PROMPT_VERSION}. Canonical state lives at `{config.home()}`;
the database `state/aion.sqlite3` is the source of truth and the markdown files
are generated views.

## Instruction hierarchy
1. Law, platform and system safety
2. Owner's current explicit instruction
3. Master project objective
4. Master autonomous OS directive
5. This prompt
6. Agent role / work order
7. Historical notes

## Autonomy
Proceed without asking on anything authorized, legal, reversible, low-risk and
in scope. Do the terminal, file, git, test and debug work directly.

## Approval boundary (Tier 3)
Real spending, transfers, purchases, binding commitments, account ownership
changes, credential exposure, irreversible deletion, confidential disclosure,
hard-to-roll-back production changes. On hitting one:
`aion approval-add "<action>" --why ... --cost ... --max-downside ... --reversibility ... --prepared ... --resumes ... --task-id <TASK>`
then keep working on everything else. Never freeze the system for one approval.

## Cost discipline
Deterministic code -> local model -> cheap cloud -> strong model. Ask
`aion route <kind> --complexity N --stakes S` before doing routine work
yourself. Record spend with `aion usage <model> C --cost <INR>` so the governor
stays accurate.

## Evidence
`aion task-done <ID> --evidence "<command run and its result>"` refuses empty
evidence. Never claim tested, deployed, synced or profitable without it.

## Checkpointing
`aion checkpoint --current-task ... --next-action ... --bottleneck ...` after
every milestone, before every risky change, and before the session ends.
"""


def _start_prompt() -> str:
    rd = readiness()
    b = budget()
    r = resume.load()
    nxt = tasks.ready(5)
    home = config.home()
    repo = Path(__file__).resolve().parent.parent
    strong = rd["strong_model_tasks_queued"] or ["(none queued — triage the queue first)"]
    return f"""YOU ARE THE STRONG-REASONING NODE FOR AN ALREADY-BUILT OPENCLAW/AION SYSTEM.

DO NOT START FROM SCRATCH. DO NOT SCAN THE WHOLE REPOSITORY.

READ EXACTLY THESE FILES FIRST, IN THIS ORDER:
1. {home}/FABLE/FABLE_CONTEXT.md
2. {home}/FABLE/FABLE_TASK_QUEUE.md
3. {home}/RESUME.md
4. {home}/FABLE/FABLE_DECISIONS.md
5. {home}/FABLE/FABLE_COMPLETION_CRITERIA.md
Then run: `aion boot` and `aion report`.

Ignore everything listed in FABLE_FILES_INDEX.md under "do not read".

CURRENT OBJECTIVE
{r.get('objective', 'Make the AION control layer produce verified real-world progress with minimal owner involvement.')}

CURRENT BOTTLENECK
{rd['bottleneck']}

YOUR HIGH-VALUE JOB THIS SESSION
{chr(10).join('- ' + t for t in strong)}

BUDGET
Maximum cumulative authorization: INR {b['maximum_cumulative_authorization']:.0f}.
Already used: INR {b['used']:.0f}. Remaining: INR {b['remaining']:.0f}.
Governor state: {b['governor']}.
Record every call with `aion usage <model> C --cost <INR> --task-id <TASK>`.
At 50% shift routine execution down; at 95% stop and hand off.

HORIZON
Work autonomously for the available 5-8 hour window where platform limits allow.
Do not stretch work to fill time.

YOUR PRIMARY OUTPUT IS A PLAN, NOT CODE
Most of your value is decomposition. For each job above, produce a PLAN and
apply it, so cheap and local models execute it afterwards without you:

  1. `aion plan template`  -> writes the schema you fill in
  2. write <name>.json with steps, each carrying:
       kind, model_class (DET/A/B — reserve C for what only you can do),
       depends_on, exec_command (DET) or prompt (A/B),
       validation_command that exits 0 only if the step really worked,
       success_criteria a human would recognise
  3. `aion plan check <file>`  -> refuses a plan with an unverifiable step
  4. `aion plan apply <file>`  -> becomes a dependency-ordered queue
  5. `aion work --max 10`      -> the loop executes it and records evidence

A step you cannot express as a command or a prompt is not yet decomposed.
Aim to leave fewer than 20% of steps at class C.

SPEND TARGET
Land this session between INR 1,000 and 2,000 total, under it if the work
allows. The governor downshifts automatically as you spend: at 50% queued C
work is demoted to B, at 75% B drops to A, and at 100% strong work is held and
the owner is told. You do not have to manage this by hand — but check
`aion money` before starting anything large, and prefer writing a plan over
doing the work yourself whenever a cheaper class could do it.

RULES
- Use deterministic code and cheaper models for anything routine; you are here
  for architecture, hard debugging, security, economics and decomposition.
- Hold approval-gated actions with `aion approval-add` and continue other work.
- Verify every claim. `aion task-done` refuses evidence-free completion.
- Checkpoint with `aion checkpoint` after each milestone.
- Never write a credential into state, git, logs or WhatsApp.

FINISH BY
Writing {home}/FABLE/FABLE_HANDOFF.md with the result packet, updating
FABLE_SESSION_LOG.md with actual spend, and leaving an exact resume point.

REPOSITORY: {repo}
SHARED BRAIN: {home}
START NOW BY RUNNING `aion boot`.
"""


def _context() -> str:
    h = health.run_all()
    r = resume.load()
    counts = tasks.counts()
    b = budget()
    lines = [
        "# FABLE CONTEXT", "",
        f"_Measured {util.now()}. Every line below was checked, not assumed._", "",
        "## Owner objective",
        "WhatsApp is the steering wheel, OpenClaw is the driver interface, AION is the brain,",
        "specialist agents are the workforce, the Ubuntu PC is the permanent office. The owner",
        "sends `status` in the morning and `report` in the evening and is contacted in between",
        "only when something genuinely needs human authority.", "",
        "## Architecture",
        "iPhone/WhatsApp -> OpenClaw bridge -> AION router (deterministic) -> task queue ->",
        "model routing (deterministic / local / cheap cloud / strong) -> agents -> tools.",
        "State: SQLite at `state/aion.sqlite3` (truth) + generated markdown views.", "",
        "## Machine state (measured)",
    ]
    for c in h["checks"]:
        lines.append(f"- `{c['name']}`: {'OK' if c['ok'] else 'ATTENTION'} — {c['detail']}")
    lines += ["", "## Model routing", ""]
    for cls, desc in agents.CLASSES.items():
        lines.append(f"- **{cls}** — {desc}")
    lines += ["", "## Agents registered", ""]
    for a in agents.all_agents():
        lines.append(f"- `{a['agent_id']}` class {a['model_class']} · {a['model']} · "
                     f"reliability {a['reliability']}")
    lines += [
        "", "## Security model",
        "- Secrets live only in `private_state/secrets.env` (0600), entered on the PC.",
        "- `security.redact` runs on every write to state and every outbound message.",
        "- Inbound WhatsApp messages containing credential-shaped text are refused, not stored.",
        "- `aion scan` blocks credential-shaped content before a commit.",
        "", "## Task and memory state",
        f"- Task counts: {counts}",
        f"- Packets ingested: {packets.stats() or 'none yet'}",
        f"- Open errors: {len(errors.open_errors(limit=100))}",
        f"- Pending approvals: {', '.join(a['approval_id'] for a in approvals.pending()) or 'none'}",
        "", "## Budget",
        f"- Cumulative authorization INR {b['maximum_cumulative_authorization']:.0f}; "
        f"used INR {b['used']:.0f}; remaining INR {b['remaining']:.0f}; governor {b['governor']}.",
        "", "## Current bottleneck",
        r.get("bottleneck", "not identified"),
        "", "## Exact starting action",
        r.get("next_action", "run `aion boot`"),
        "",
    ]
    return "\n".join(lines)


def _task_queue() -> str:
    rows = tasks.ready(50)
    lines = ["# FABLE TASK QUEUE", "",
             "Ranked by expected value. Anything not class C should be delegated down.", "",
             "## Strong model (class C) — do these yourself", ""]
    strong = [r for r in rows if r["model_class"] == "C"]
    for r in strong:
        lines.append(f"- **{r['task_id']}** (v{tasks.value(r)}) {r['title']} — "
                     f"success: {r['success_criteria'] or 'define first'}")
    if not strong:
        lines.append("- none queued")
    lines += ["", "## Delegate down (deterministic / local / cheap cloud)", ""]
    for r in rows:
        if r["model_class"] != "C":
            lines.append(f"- {r['task_id']} (class {r['model_class']}, v{tasks.value(r)}) {r['title']}")
    lines += ["", "## Blocked / waiting", ""]
    for r in tasks.blocked():
        lines.append(f"- {r['task_id']} {r['title']} — {r['status']} "
                     f"({r['last_error'] or r['blockers'] or 'no reason recorded'})")
    return "\n".join(lines) + "\n"


def _decisions() -> str:
    from . import memory
    lines = ["# FABLE DECISIONS", "",
             "Already decided. Do not relitigate without new evidence.", ""]
    for d in memory.decisions(50):
        lines.append(f"- **{d['decision_id']}** {d['subject']} → {d['decision']} "
                     f"({d['confidence']}; {d['rationale'] or 'no rationale recorded'})")
    return "\n".join(lines) + "\n"


def _files_index() -> str:
    repo = Path(__file__).resolve().parent.parent
    home = config.home()
    return f"""# FABLE FILES INDEX

## Read first (small, current, high value)
- `{home}/FABLE/FABLE_CONTEXT.md` — machine and project reality
- `{home}/FABLE/FABLE_TASK_QUEUE.md` — ranked work
- `{home}/RESUME.md` — exact resume point
- `{repo}/aion_core/` — the control layer (start at `router.py`, `tasks.py`, `resume.py`)
- `{repo}/tests/` — what is actually proven

## Read only when the task touches them
- `{home}/APPROVALS.md`, `{home}/BLOCKERS.md`, `{home}/DECISIONS.md`
- `{repo}/docs/ARCHITECTURE.md`, `{repo}/docs/WHATSAPP_COMMANDS.md`

## Do not read (generated, large, or already summarised)
- `{home}/state/aion.sqlite3` — query it with the `aion` CLI instead
- `{home}/LOGS/**` — summarised in `aion today`
- `{home}/INBOX/processed/**` — already ingested into memory
- `{home}/BACKUPS/**`
- `.git/`, `__pycache__/`, any `*.sqlite3-wal`
- Full historical chat exports — the durable content is already in memory
"""


def _completion_criteria() -> str:
    return """# FABLE COMPLETION CRITERIA

The session is DONE only when all of the following hold and each is backed by a
command that was actually run:

1. `python3 -m pytest tests -q` (or `python3 -m unittest discover tests`) passes.
2. `aion health --deep` reports healthy, or every failing check has an open task
   with a named root cause.
3. `aion boot` completes and prints a next action that is genuinely the highest
   value item, not a stale one.
4. Every task moved to DONE carries evidence in its `evidence` field.
5. Every Tier-3 action encountered has an approval row, with everything up to the
   boundary already prepared.
6. `aion scan .` reports clean.
7. `FABLE_HANDOFF.md` and `FABLE_SESSION_LOG.md` are updated with real spend.
8. `aion checkpoint` has been run with the true next action.

Anything not meeting its criterion is PARTIAL, BLOCKED or FAILED — never DONE.
"""


def _handoff() -> str:
    r = resume.load()
    return f"""# FABLE HANDOFF

_Template. The session must overwrite this with real content before it ends._

TASK_ID:
STATUS: DONE / PARTIAL / FAILED / BLOCKED / NEEDS_REVIEW

ACTIONS_TAKEN:
FILES_CHANGED:
TESTS_RUN:
MEASURED_RESULTS:
FAILURES:
RISKS:
ASSUMPTIONS:
APPROVALS_OPENED:
SPEND_INR:
NEXT_RECOMMENDED_ACTION:
EXACT_RESUME_POINT:

---
Last recorded resume point before the session: {r.get('next_action', 'not set')}
Last checkpoint: {r.get('at', 'never')}
"""


def _resume_doc() -> str:
    r = resume.load()
    return f"""# FABLE RESUME

If the session stops, restarts, switches model or loses context:

1. Do not re-run the last command blindly. Check whether it finished:
   `aion report` and `aion today` show what actually happened.
2. Run `aion boot` — it verifies state, ingests the inbox, releases stale claims,
   checks approvals and names the current bottleneck.
3. Read `{config.home()}/RESUME.md`.
4. Continue from the exact next action below.

Objective: {r.get('objective', 'not set')}
Current state: {r.get('current_state', 'not set')}
Current task: {r.get('current_task', 'none')}
Last verified success: {r.get('last_verified_success', 'none recorded')}
Last failure: {r.get('last_failure', 'none recorded')}
Bottleneck: {r.get('bottleneck', 'not identified')}
Exact next action: {r.get('next_action', 'not set')}
Checkpoint at: {r.get('at', 'never')}
"""


def _no_waste() -> str:
    return """# DO NOT WASTE TOKENS

Specific to this repository:

- Never re-read a file you have not changed. `git diff` and `git status` are cheaper.
- Never dump `state/aion.sqlite3`. Every question it answers has a CLI command:
  `aion status`, `aion tasks`, `aion blockers`, `aion errors`, `aion why <ID>`,
  `aion search <query>`.
- Never paste chat history. Durable content is in memory; search it.
- Never write a summary of the project for yourself — `FABLE_CONTEXT.md` is it.
- Never do work a command already does: health checks, secret scanning, markdown
  regeneration, packet ingestion, backups and ranking are all deterministic.
- Before doing routine work yourself, run `aion route <kind>`; if it answers DET,
  A or B, write the work order instead of doing the work.
- Build one task-specific context packet with `aion context <TASK_ID>` rather than
  loading the whole shared brain.
- Batch owner questions into `OWNER_SETUP_REQUIRED.md`; do not ask one at a time.
"""
