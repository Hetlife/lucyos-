"""WhatsApp command router.

The owner types shortcuts or ordinary language.  This layer is deterministic:
no model call is needed to answer `status`, `money`, `approve A-142` and the
rest, which is why the remote control keeps working when every model is down.

Three hard rules enforced here:
  * an inbound message that contains credential-shaped text is refused and the
    raw text is never persisted;
  * casual conversation never counts as authorization — only the exact
    `APPROVE <ID>` / `DENY <ID>` form decides an approval;
  * every consequential owner instruction is written back to local state.
"""
from __future__ import annotations

import re

from . import approvals, db, health, memory, metrics, reports, resume, security, tasks, util

SECRET_REFUSAL = (
    "I did not store that message. It looks like it contains a credential.\n"
    "Never send passwords, API keys, OTPs, recovery codes or card details here.\n"
    "Put the value directly into the secret store on the PC "
    "(`aion secrets set <NAME>`), then reply `done`."
)

HELP = """AION commands
status · today · money · tasks · blockers · errors · agents
approve <ID> · reject <ID> (same as deny)
pause · resume · safe mode · safe mode off
deep check · why <ID> · report · help

Anything else is read as ordinary language and matched to the nearest command.
Never send secrets here."""

# Ordinary-language triggers.  Ordered: first match wins.
INTENTS = [
    ("approve", re.compile(r"(?i)\b(approve|approved|go ahead with|yes to)\b\s*(?P<id>[A-Za-z]+-[A-Za-z0-9]{1,12})")),
    ("deny", re.compile(r"(?i)\b(deny|denied|reject|rejected|no to|cancel)\b\s*(?P<id>[A-Za-z]+-[A-Za-z0-9]{1,12})")),
    ("why", re.compile(r"(?i)\bwhy\b.*?(?P<id>[A-Za-z]+-[A-Za-z0-9]{1,12})")),
    ("deep_check", re.compile(r"(?i)\b(deep check|deepcheck|full check|verify everything|deep verify)\b")),
    ("safe_mode_off", re.compile(r"(?i)\b(safe mode off|exit safe mode|unsafe mode|leave safe mode)\b")),
    ("safe_mode", re.compile(r"(?i)\b(safe mode|safemode|lock down|lockdown)\b")),
    ("pause", re.compile(r"(?i)\b(pause|hold everything|stop automation|freeze)\b")),
    ("resume", re.compile(r"(?i)\b(resume|unpause|continue|carry on|start again)\b")),
    ("report", re.compile(r"(?i)\b(report|full report|detailed report|end of day|evening report)\b")),
    ("today", re.compile(r"(?i)\b(today|what happened|since this morning|day so far)\b")),
    ("money", re.compile(r"(?i)\b(money|revenue|profit|earnings|costs?|spend|budget|finance)\b")),
    ("blockers", re.compile(r"(?i)\b(blockers?|blocked|what do you need|need from me|waiting on me)\b")),
    ("errors", re.compile(r"(?i)\b(errors?|failures?|what broke|crashes?)\b")),
    ("agents", re.compile(r"(?i)\b(agents?|workers?|who is working)\b")),
    ("tasks", re.compile(r"(?i)\b(tasks?|queue|priorities|what next|to ?do)\b")),
    ("status", re.compile(r"(?i)\b(status|how are things|sitrep|update|health|everything ok)\b")),
    ("help", re.compile(r"(?i)\b(help|commands|what can you do)\b")),
]

APPROVE_STRICT = re.compile(r"(?i)^\s*(approve|deny|reject)\s+(?P<id>[a-z]+-[a-z0-9]{1,12})\s*$")


def handle(message: str, *, sender: str = "owner") -> str:
    """Route one inbound owner message and return the reply text."""
    raw = (message or "").strip()
    if not raw:
        return HELP

    findings = security.scan_text(raw)
    if findings:
        # Log the refusal without the payload.
        db.log_event(sender, "whatsapp.secret_refused", ",".join(sorted({f["kind"] for f in findings})))
        return SECRET_REFUSAL

    db.log_event(sender, "whatsapp.in", raw[:200])

    strict = APPROVE_STRICT.match(raw)
    if strict:
        verb = strict.group(1).lower()
        return _decide(strict.group("id"), "APPROVED" if verb == "approve" else "DENIED", sender)

    lowered = raw.lower().strip(" .!?")
    simple = {
        "status": _status, "today": reports.today, "money": reports.money,
        "tasks": reports.task_list, "blockers": reports.blockers, "errors": reports.error_list,
        "agents": reports.agent_list, "report": reports.full_report, "help": lambda: HELP,
        "pause": lambda: _pause(sender), "resume": lambda: _resume(sender),
        "safe mode": lambda: _safe_mode(True, sender), "safe mode off": lambda: _safe_mode(False, sender),
        "deep check": _deep_check,
    }
    if lowered in simple:
        return simple[lowered]()

    for name, pattern in INTENTS:
        m = pattern.search(raw)
        if not m:
            continue
        if name == "approve":
            return _decide(m.group("id"), "APPROVED", sender)
        if name == "deny":
            return _decide(m.group("id"), "DENIED", sender)
        if name == "why":
            return memory.why(m.group("id"))
        return {
            "status": _status, "today": reports.today, "money": reports.money,
            "tasks": reports.task_list, "blockers": reports.blockers,
            "errors": reports.error_list, "agents": reports.agent_list,
            "report": reports.full_report, "help": lambda: HELP,
            "deep_check": _deep_check, "pause": lambda: _pause(sender),
            "resume": lambda: _resume(sender),
            "safe_mode": lambda: _safe_mode(True, sender),
            "safe_mode_off": lambda: _safe_mode(False, sender),
        }[name]()

    # Unrecognised: record it as an inbox item rather than guessing an action.
    task_id = tasks.create(raw[:120], status="INBOX", description=f"Owner message via WhatsApp from {sender}",
                           human_dependence=0.5)
    return (f"I did not recognise that as a command, so I saved it as {task_id} for triage "
            f"rather than guessing.\n\n{HELP}")


def _status() -> str:
    return reports.status()


def _decide(approval_id: str, decision: str, sender: str) -> str:
    try:
        result = approvals.decide(approval_id, decision, by=sender)
    except approvals.ApprovalError as exc:
        pend = approvals.pending()
        return (f"{exc}. Pending right now: "
                f"{', '.join(r['approval_id'] for r in pend) or 'nothing'}.")
    verb = "approved" if decision == "APPROVED" else "denied"
    if not result["changed"]:
        if result.get("error"):
            return (f"{result['approval_id']} is still PENDING — the remote system did not "
                    f"confirm the decision ({result['error']}). Nothing changed locally; "
                    f"try again once the connection is back.")
        return (f"{result['approval_id']} was already {result['status'].lower()} — "
                f"nothing re-applied (duplicate reply is safe).")
    row = approvals.get(result["approval_id"])
    tail = ""
    if result["task_id"]:
        tail = (f"\nResuming {result['task_id']} at: {row['resumes'] or 'the prepared step'}"
                if decision == "APPROVED" else f"\n{result['task_id']} cancelled.")
    reports.render_markdown_surfaces()
    return f"{result['approval_id']} {verb}. {row['action']}{tail}"


def _pause(sender: str) -> str:
    db.set_meta("paused", "1")
    db.log_event(sender, "control.pause")
    memory.decide("automation pause", "consequential automation paused by owner",
                  rationale="owner sent pause via WhatsApp", made_by=sender,
                  confidence="VERIFIED_FACT")
    return ("Paused. Consequential automation is held; read-only monitoring continues. "
            "Send `resume` to restart.")


def _resume(sender: str) -> str:
    db.set_meta("paused", "0")
    db.log_event(sender, "control.resume")
    state = resume.boot()
    return ("Resumed.\n" + reports.status() + "\n\nNext: " +
            state["resume"].get("next_action", "not set"))


def _safe_mode(on: bool, sender: str) -> str:
    db.set_meta("safe_mode", "1" if on else "0")
    db.log_event(sender, f"control.safe_mode_{'on' if on else 'off'}")
    if on:
        memory.decide("safe mode", "spending, outbound messaging and external writes disabled",
                      rationale="owner requested safe mode", made_by=sender,
                      confidence="VERIFIED_FACT")
        return ("SAFE MODE ON. No spending, no outbound messages, no external writes. "
                "Local analysis, testing and reporting continue.")
    return "Safe mode off. Normal tiered autonomy restored (Tier 3 still needs your approval)."


def _deep_check() -> str:
    report = health.run_all(deep=True)
    lines = ["DEEP CHECK", ""]
    for c in report["checks"]:
        lines.append(f"{'OK  ' if c['ok'] else 'FAIL'} {c['name']}: {c['detail']}")
    lines.append("")
    lines.append("Verdict: " + ("all checks pass" if report["healthy"]
                                else "failing — " + ", ".join(report["failing"])))
    return security.redact("\n".join(lines))


def is_paused() -> bool:
    return db.get_meta("paused", "0") == "1"


def is_safe_mode() -> bool:
    return db.get_meta("safe_mode", "0") == "1"
