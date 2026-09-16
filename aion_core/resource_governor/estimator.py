"""Task resource-size estimation (directive sections 10 and 23).

Two signals, blended:

  * a deterministic heuristic from the task itself (kind, model class,
    description length) — available for every task, even one that has never
    run before;
  * historical actual consumption for tasks of the same `kind`, read from
    the model-usage table `worker.py`/`metrics.py` already populate — no new
    telemetry collection needed, just a query over data that already exists.

This never claims precision it doesn't have.  `estimate()` always returns a
bucket plus the evidence behind it, so a caller (and the owner, via `why`)
can see whether a size came from real history or a guess.
"""
from __future__ import annotations

from .. import agents, db

SIZES = ("TINY", "SMALL", "MEDIUM", "LARGE", "VERY_LARGE", "UNKNOWN")

# Token-count bucket boundaries.  Deliberately approximate and configurable
# in spirit (see flags.py for the pattern) — not claimed to be exact.
_BUCKETS = [
    ("TINY", 1_000),
    ("SMALL", 5_000),
    ("MEDIUM", 20_000),
    ("LARGE", 60_000),
]


def _bucket_for(estimated: float) -> str:
    for name, ceiling in _BUCKETS:
        if estimated < ceiling:
            return name
    return "VERY_LARGE"


def _heuristic_tokens(task: dict) -> float:
    text_len = len(task.get("description") or "") + len(task.get("title") or "")
    base = text_len * 1.3  # crude chars->tokens ratio; a starting point only
    kind = (task.get("kind") or "").lower()
    if kind in agents.STRONG_KINDS:
        base = max(base, 15_000)
    model_class = task.get("model_class") or "B"
    if model_class == "C":
        base = max(base, 10_000)
    elif model_class == "D":
        base = 0  # an owner decision consumes no model capacity
    return base


def historical_average_tokens(kind: str) -> float | None:
    if not kind:
        return None
    row = db.connect().execute(
        "SELECT AVG(input_tokens + output_tokens) avg_tokens, COUNT(*) n "
        "FROM model_usage JOIN tasks USING(task_id) "
        "WHERE tasks.kind=? AND (model_usage.input_tokens > 0 OR model_usage.output_tokens > 0)",
        (kind,)).fetchone()
    if row is None or not row["n"] or row["avg_tokens"] is None:
        return None
    return float(row["avg_tokens"])


def estimate(task) -> dict:
    """Returns {"size", "estimated_tokens", "basis"} — never a bare label."""
    t = dict(task) if not isinstance(task, dict) else task
    if not t.get("title") and not t.get("description") and not t.get("kind"):
        return {"size": "UNKNOWN", "estimated_tokens": None, "basis": "no task signal available"}

    heuristic = _heuristic_tokens(t)
    history = historical_average_tokens(t.get("kind") or "")
    if history is not None:
        # Blend: history is real observed cost for this kind of work, so it
        # dominates once there is enough of it to trust; the heuristic still
        # nudges the estimate for an unusually large individual task.
        estimated = 0.7 * history + 0.3 * heuristic
        basis = f"blended: {round(history)} historical avg tokens for kind={t.get('kind')!r}"
    else:
        estimated = heuristic
        basis = "heuristic only: no historical data yet for this task kind"
    return {"size": _bucket_for(estimated), "estimated_tokens": round(estimated), "basis": basis}
