"""Deterministic query construction and lexical (FTS5/LIKE) candidate search.

This is the "no frontier-model call needed" half of recall.  Everything here
is regexes, SQL and sorting -- the same DET-tier discipline the rest of
aion_core already applies to routing (aion_core/agents.py) and commands
(aion_core/router.py).

CONFIDENCE_ORDER (imported from .models) must match aion_core.memory.CONFIDENCE
exactly, since a minimum_confidence filter is meaningless if the two modules
disagree on what "better" means.  Checked by
tests/test_recall.py::test_confidence_order_matches_memory_module rather than
by an import-time assert, so a mismatch fails a test run, not every process
that happens to import this module.
"""
from __future__ import annotations

import re

from .models import CONFIDENCE_ORDER, RecallCandidate, RecallQuery, confidence_rank

_STOPWORDS = frozenset({
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with",
    "is", "are", "be", "this", "that", "it", "as", "by", "at", "from",
    "into", "not", "no", "do", "does", "did", "if", "then", "than", "but",
    "so", "such", "its", "was", "were", "will", "would", "should", "can",
    "could", "has", "have", "had", "must", "never", "always", "about",
})
_TOKEN = re.compile(r"[A-Za-z0-9_]{3,}")


def extract_keywords(*texts: str, max_terms: int = 12) -> list[str]:
    """Deterministic keyword extraction: tokenize, drop stopwords and short
    tokens, rank by frequency across all given texts (ties keep first-seen
    order -- Python dicts preserve insertion order).

    This is not NLP.  It is the smallest thing that turns four free-text task
    fields into a usable FTS5 query, which is the actual gap the LucyOS
    memory recall prompt names: context.py used to search on the task title
    alone.
    """
    counts: dict[str, int] = {}
    for text in texts:
        for tok in _TOKEN.findall(text or ""):
            low = tok.lower()
            if low in _STOPWORDS:
                continue
            counts[low] = counts.get(low, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: -kv[1])
    return [tok for tok, _n in ranked[:max_terms]]


def fts_query_string(keywords: list[str]) -> str:
    """Same quoting convention aion_core.memory.search already uses, so FTS5
    behaviour doesn't silently diverge between the old and new query paths."""
    return " ".join(f'"{tok}"' for tok in keywords if tok.strip())


def from_task(row, *, bottleneck: str = "", limit: int = 6, token_budget: int = 1200) -> RecallQuery:
    """Build a RecallQuery from a task row's title, description, success
    criteria, next action and (optionally) the current resume bottleneck --
    the multi-field construction the spec asks for, done deterministically.

    `row` is a sqlite3.Row from the tasks table; every field indexed here has
    a NOT NULL DEFAULT '' in the schema, so plain indexing is safe.
    """
    texts = [row["title"], row["description"], row["success_criteria"],
             row["next_action"], bottleneck]
    keywords = extract_keywords(*texts)
    return RecallQuery(
        query_text=fts_query_string(keywords),
        project=row["project"] or None,
        limit=limit,
        token_budget=int(token_budget),
        task_id=row["task_id"],
    )


def _confidence_clause(minimum_confidence: str | None) -> tuple[str, list]:
    if not minimum_confidence:
        return "", []
    threshold = confidence_rank(minimum_confidence)
    allowed = [c for c in CONFIDENCE_ORDER if confidence_rank(c) <= threshold]
    placeholders = ",".join("?" for _ in allowed)
    return f" AND m.confidence IN ({placeholders})", allowed


def candidates(q: RecallQuery, *, fetch_limit: int) -> list[RecallCandidate]:
    """Run the deterministic filters + FTS5 (or LIKE fallback) search.

    Mirrors aion_core.memory.search's own fallback discipline (try FTS5,
    fall back to LIKE on any exception, never raise out of a search call) so
    recall never becomes a new way for memory lookup to break.
    """
    from .. import db  # local import: avoid a hard import-time cycle with aion_core.db

    conn = db.connect()
    conf_clause, conf_params = _confidence_clause(q.minimum_confidence)

    if db.HAS_FTS and q.query_text.strip():
        sql = ("SELECT m.* FROM memory_fts f JOIN memory m ON m.rowid = f.rowid "
               "WHERE memory_fts MATCH ?")
        params: list = [q.query_text]
        if q.project:
            sql += " AND m.project=?"
            params.append(q.project)
        if q.memory_kinds:
            sql += f" AND m.kind IN ({','.join('?' for _ in q.memory_kinds)})"
            params += list(q.memory_kinds)
        if q.source:
            sql += " AND m.source=?"
            params.append(q.source)
        sql += conf_clause
        params += conf_params
        sql += " ORDER BY rank LIMIT ?"
        params.append(fetch_limit)
        try:
            rows = conn.execute(sql, params).fetchall()
            return [RecallCandidate(memory_id=r["memory_id"], source_method="lexical_fts",
                                    row=dict(r)) for r in rows]
        except Exception:
            pass  # fall through to LIKE, exactly like memory.search does

    like_terms = q.query_text.replace('"', "").split() or [""]
    sql = "SELECT * FROM memory WHERE 1=1"
    params = []
    for term in like_terms[:6]:  # bound how many LIKE clauses one query can grow to
        sql += " AND (title LIKE ? OR body LIKE ? OR tags LIKE ?)"
        like = f"%{term}%"
        params += [like, like, like]
    if q.project:
        sql += " AND project=?"
        params.append(q.project)
    if q.memory_kinds:
        sql += f" AND kind IN ({','.join('?' for _ in q.memory_kinds)})"
        params += list(q.memory_kinds)
    if q.source:
        sql += " AND source=?"
        params.append(q.source)
    sql += conf_clause
    params += conf_params
    sql += " ORDER BY at DESC LIMIT ?"
    params.append(fetch_limit)
    rows = conn.execute(sql, params).fetchall()
    return [RecallCandidate(memory_id=r["memory_id"], source_method="lexical_like",
                            row=dict(r)) for r in rows]
