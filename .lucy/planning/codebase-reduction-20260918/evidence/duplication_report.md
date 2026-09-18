# Duplication scan report (S-42)

Advisory evidence from `scripts/duplication_scan.py`. Reports only; nothing was deleted or modified by generating this file.

Scanned 68 Python files under `aion_core`, `bridges`, `scripts`.

## Duplicate function bodies

Functions whose normalized AST body (source locations ignored, docstring stripped) is identical to another function's, and whose body spans more than 15 lines.

None found.

## Repeated retry/backoff, health-check, validation shapes

Name-pattern signal: the same functional category implemented by name in two or more distinct files. Not literal duplication -- a candidate list for a human to judge whether consolidation is warranted.

- **validation**: 5 functions across 3 files (`aion_core/architecture.py`, `aion_core/skills.py`, `aion_core/worker.py`)
  - `aion_core/architecture.py:39` `validate_proposal`
  - `aion_core/skills.py:203` `validate_registry`
  - `aion_core/skills.py:255` `validate_manifest`
  - `aion_core/skills.py:408` `validate_catalog`
  - `aion_core/worker.py:557` `_validate`
