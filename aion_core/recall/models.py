"""Data shapes for the recall engine.

Everything downstream (lexical search, a future vector store, fusion,
reranking, evidence selection, the token budgeter) speaks these four types
so no caller ever needs to know which retrieval method actually produced a
result.  A worker or context packet only ever sees RecallEvidence.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Mirrors aion_core.memory.CONFIDENCE.  Duplicated as a tuple, not imported,
# so this module has no import-time dependency on memory.py; recall/lexical.py
# is the one place that actually needs both and asserts they match (see its
# module docstring).
CONFIDENCE_ORDER = ("VERIFIED_FACT", "SUPPORTED_FACT", "INFERENCE", "ESTIMATE",
                    "ASSUMPTION", "HYPOTHESIS", "UNKNOWN")


def confidence_rank(confidence: str) -> int:
    """Lower is better.  An unrecognised label ranks last, not highest."""
    try:
        return CONFIDENCE_ORDER.index(confidence)
    except ValueError:
        return len(CONFIDENCE_ORDER)


@dataclass
class RecallQuery:
    """What the caller wants back.

    query_text is already deterministically built (see lexical.from_task) by
    the time it reaches the engine -- the engine never does its own NLP.
    """
    query_text: str = ""
    project: str | None = None
    memory_kinds: tuple[str, ...] = ()
    entities: tuple[str, ...] = ()
    source: str | None = None
    source_date: str | None = None
    valid_at: str | None = None          # reserved: temporal filtering, not implemented (Phase 8)
    task_id: str | None = None
    limit: int = 6
    token_budget: int = 1200
    minimum_confidence: str | None = None


@dataclass
class RecallCandidate:
    """One raw hit from one retrieval method, before fusion."""
    memory_id: str
    source_method: str            # "lexical_fts" | "lexical_like" | "vector" (future)
    row: dict                     # the memory table row, as a plain dict


@dataclass
class RecallEvidence:
    """What actually reaches a worker or context packet -- an excerpt, not a
    full memory body, and never just a title."""
    memory_id: str
    source: str
    source_date: str | None
    confidence: str
    project: str
    title: str
    relevant_excerpt: str
    score: float
    retrieval_methods: tuple[str, ...]
    validity: str = "current"      # reserved: superseded/historical, Phase 8
    entity_refs: tuple[str, ...] = ()


@dataclass
class RecallResult:
    query: RecallQuery
    evidence: list[RecallEvidence] = field(default_factory=list)
    candidates_generated: dict = field(default_factory=dict)   # {"lexical": 20, "vector": 0}
    degraded: bool = False
    degraded_reasons: list[str] = field(default_factory=list)
    estimated_tokens: int = 0
    elapsed_ms: float = 0.0
