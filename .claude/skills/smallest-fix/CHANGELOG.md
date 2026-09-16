# smallest-fix changelog

## 1.0.0 — 2026-09-16

First release. Written independently for LucyOS after evaluating
`DietrichGebert/ponytail` via the `learnrepo` skill
(`/root/openclaw/shared_brain/learnrepo/investigations/better-programmer-repo-eval/report.md`).
That investigation's own recommendation was `prototype`, not merge — ponytail
is a well-built external plugin, but it has nothing to do with LucyOS's
runtime and installing it edits a developer's global Claude settings, a
side effect out of scope for that request. This skill instead captures the
one part of the idea worth having as LucyOS-owned, testable code: check
before you write.

No text, code, or structure was copied from ponytail. The wording, the
ladder's exact steps, and the enforcement mechanism (an AST-based checker
tied to `aion_core/util.py`'s actual API) are original to this skill.

Added:

- `SKILL.md` — the five-step ladder and the boundary between "smaller" and
  "worse" (validation, error handling, security, evidence, tests are never
  the thing to cut).
- `scripts/check_reinvention.py` — parses Python files with `ast` (not
  regex-over-text) and flags calls that duplicate `aion_core/util.py`:
  UTC timestamps, id generation, sha256 hashing, atomic writes, JSON
  read/write. `aion_core/util.py` itself is always exempt.
- `tests/test_smallest_fix_skill.py` in the LucyOS suite.

Known limitation, by design rather than oversight: the checker matches the
exact call shape LucyOS actually uses (`datetime.now(timezone.utc)` after
`from datetime import datetime, timezone`). An aliased import
(`from datetime import datetime as dt`) or the fully-qualified
`datetime.datetime.now(...)` form will not be caught. Chasing every import
alias would need real symbol resolution for a small gain, which is exactly
the kind of scope this skill argues against; a missed lead is preferable to
a checker complex enough to need its own maintenance.
