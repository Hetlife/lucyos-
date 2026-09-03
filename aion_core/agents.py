"""Agent registry and model routing.

Routing rule from the directive, applied in order:
deterministic code -> local model (class A) -> cheap cloud (B) -> strong (C)
-> owner (D).  A task only reaches a more expensive class when the cheaper
one cannot reliably do it.
"""
from __future__ import annotations

from . import db, util

CLASSES = {
    "DET": "deterministic code — exact, repeatable, zero model cost",
    "A": "local model (Ollama) — classification, extraction, formatting, summarising",
    "B": "cheap cloud model — routine coding, standard research, normal structured work",
    "C": "strong reasoning model — architecture, hard debugging, security, economics",
    "D": "owner — a genuine human decision boundary",
}
ORDER = ["DET", "A", "B", "C", "D"]

# Task kinds that deterministic code must handle; sending these to a model is waste.
DETERMINISTIC_KINDS = {
    "file_write", "file_move", "hash", "backup", "git", "health_check", "count",
    "schema_validate", "dedupe", "timestamp", "parse_json", "diff", "test_run",
}
LOCAL_KINDS = {
    "classify", "extract", "format", "summarize", "log_parse", "monitor",
    "dedupe_text", "translate_simple", "tag",
}
STRONG_KINDS = {
    "architecture", "decompose", "security_review", "hard_debug", "finance_reason",
    "novel_research", "adversarial_review", "strategy",
}
OWNER_KINDS = {"spend", "contract", "credential", "account_change", "irreversible"}

DEFAULT_AGENTS = [
    dict(agent_id="openclaw", role="orchestrator", model="openclaw", model_class="DET",
         cost_class="none", capabilities="state,routing,execution,resume,approvals,reporting",
         max_complexity=5, allowed_tools="fs,git,shell,http"),
    dict(agent_id="ollama-local", role="worker", model="llama3.1:8b", model_class="A",
         cost_class="none", capabilities="classify,extract,format,summarize,log_parse,monitor,tag",
         max_complexity=2, allowed_tools="fs_read"),
    dict(agent_id="cloud-sonnet", role="worker", model="claude-sonnet-5", model_class="B",
         cost_class="medium", capabilities="code,research,debug,write,plan_execute",
         max_complexity=4, allowed_tools="fs,shell"),
    dict(agent_id="cloud-cheap", role="worker", model="claude-haiku-4-5-20251001", model_class="B",
         cost_class="low", capabilities="code,research,debug,write", max_complexity=3,
         allowed_tools="fs,shell"),
    dict(agent_id="cloud-strong", role="reasoner", model="claude-opus-5", model_class="C",
         cost_class="high", capabilities="architecture,decompose,security_review,hard_debug,"
         "finance_reason,novel_research,adversarial_review,strategy",
         max_complexity=5, allowed_tools="fs,shell,http"),
    dict(agent_id="owner", role="authority", model="human", model_class="D",
         cost_class="scarce", capabilities="approve,pay,sign,verify_identity",
         max_complexity=5, allowed_tools="whatsapp"),
]


def register(**kw) -> str:
    conn = db.connect()
    cols = list(kw)
    conn.execute(
        f"INSERT INTO agents({','.join(cols)}) VALUES({','.join('?' * len(cols))}) "
        f"ON CONFLICT(agent_id) DO UPDATE SET {', '.join(f'{c}=excluded.{c}' for c in cols if c != 'agent_id')}",
        [kw[c] for c in cols])
    conn.commit()
    return kw["agent_id"]


def seed_defaults() -> int:
    for spec in DEFAULT_AGENTS:
        register(**spec)
    return len(DEFAULT_AGENTS)


def all_agents() -> list:
    return db.connect().execute("SELECT * FROM agents ORDER BY model_class, agent_id").fetchall()


def get(agent_id: str):
    return db.connect().execute("SELECT * FROM agents WHERE agent_id=?", (agent_id,)).fetchone()


def route(kind: str, complexity: int = 2, stakes: str = "low", ambiguity: str = "low") -> dict:
    """Pick the cheapest class that can reliably do the work.

    Returns {"model_class", "agent_id", "reason"} — never a bare string, so the
    decision is auditable in DECISIONS.md.
    """
    kind = (kind or "").strip().lower()
    reason = []
    if kind in OWNER_KINDS:
        return _pick("D", "action crosses an owner authority boundary")
    if kind in DETERMINISTIC_KINDS:
        return _pick("DET", "exact repeatable operation — deterministic code is cheaper and more reliable")
    cls = "A" if kind in LOCAL_KINDS else "B"
    if kind in STRONG_KINDS:
        cls, reason = "C", ["task kind requires strong reasoning"]
    if complexity >= 4 and cls in ("DET", "A", "B"):
        cls = "C"
        reason.append(f"complexity {complexity} exceeds cheap-model reliability")
    if stakes in ("high", "critical") and cls in ("A", "B"):
        cls = "C"
        reason.append(f"{stakes} stakes justify strong review")
    if ambiguity == "high" and cls == "A":
        cls = "B"
        reason.append("ambiguity above local-model capability")
    return _pick(cls, "; ".join(reason) or f"routine {kind or 'work'} within class {cls} capability")


def preferred(cls: str) -> str | None:
    """The agent the owner wants for a class, when more than one qualifies."""
    return db.get_meta(f"preferred_agent_{cls}", "") or None


def set_preferred(cls: str, agent_id: str) -> None:
    db.set_meta(f"preferred_agent_{cls}", agent_id)
    db.log_event("aion", "route.preferred", cls, agent_id)


def _pick(cls: str, reason: str) -> dict:
    conn = db.connect()
    want = preferred(cls)
    row = None
    if want:
        row = conn.execute(
            "SELECT agent_id FROM agents WHERE agent_id=? AND enabled=1", (want,)).fetchone()
    if row is None:
        row = conn.execute(
            "SELECT agent_id FROM agents WHERE model_class=? AND enabled=1 "
            "ORDER BY reliability DESC LIMIT 1", (cls,)).fetchone()
    return {"model_class": cls, "agent_id": row["agent_id"] if row else None, "reason": reason}


def escalate(current_class: str, why: str) -> dict:
    """Move exactly one step up the ladder — never straight to the owner."""
    if current_class not in ORDER:
        current_class = "A"
    idx = ORDER.index(current_class)
    nxt = ORDER[min(idx + 1, ORDER.index("C"))]
    db.log_event("aion", "route.escalate", f"{current_class}->{nxt}", why)
    return _pick(nxt, f"escalated from {current_class}: {why}")


def record_run(agent_id: str, success: bool, task_id: str | None = None) -> None:
    conn = db.connect()
    row = get(agent_id)
    if row is None:
        return
    runs = row["runs"] + 1
    failures = row["failures"] + (0 if success else 1)
    reliability = round(1.0 - failures / runs, 3)
    conn.execute(
        "UPDATE agents SET runs=?, failures=?, reliability=?, last_health_check=?, "
        "current_task=?, status=? WHERE agent_id=?",
        (runs, failures, reliability, util.now(), task_id, "IDLE", agent_id))
    conn.commit()
