---
name: smallest-fix
description: Pushes toward the smallest change that actually solves the stated problem, before writing new code — for writing, refactoring, fixing, or reviewing anything in this repo. Use it whenever adding a function, a module, a dependency, or an abstraction; whenever a diff is growing past what the task needs; or when reviewing a change for unnecessary scope. It never strips validation, error handling, security checks, evidence requirements, or tests to make a diff smaller — those are the actual job, not overhead. Independently authored for LucyOS; not derived from or a port of any third-party "lazy dev" tool.
---

# smallest-fix — write the smallest thing that is actually correct

LucyOS already applies this idea to model routing: DET → local → cheap cloud
→ strong model → owner, cheapest capable path first
(`aion_core/agents.py`, `README.md`). This skill applies the same instinct to
writing code: the cheapest capable *change* first, not the cheapest capable
*model*.

Most unnecessary code is not wrong, just unearned. A new abstraction for one
caller, a helper that duplicates something three modules already have, a
config system for a value that never changes — none of these are bugs. They
are debt nobody asked to take on, and every one of them is a smaller,
easier decision before it exists than after it has three callers.

## The ladder

Work down until something actually answers the requirement. Stop there —
going further is not more thorough, it is more to maintain.

1. **Does this need to exist?** State what the task actually requires. If a
   smaller or already-satisfied version of the request would work, say so
   instead of building the larger thing nobody asked for.
2. **Is it already here?** `grep -rn` for the function, pattern, or table
   this would duplicate. LucyOS is a small, dense codebase
   (`aion_core/`, ~30 modules) — check before adding a twin.
3. **Does the standard library do this?** LucyOS runs on Python 3.9+
   standard library only, by policy, not by accident (`README.md`). This
   step is not optional here the way it might be elsewhere.
4. **Is there a one-line or few-line fix that fully satisfies the
   requirement?** Take it. A comment explaining *why* it's short is worth
   more than the short version making a future reader guess.
5. **Only then, build the minimum working version**, with the tests and
   error handling the task actually needs.

## Run the deterministic half of step 2

Reading every module before writing four lines does not scale. This does:

```bash
python3 .claude/skills/smallest-fix/scripts/check_reinvention.py <changed-files-or-dirs>
```

It parses each file (never regex-over-raw-text — see
`.claude/skills/learnrepo/references/security-screening.md` for why a
regex-only screen produces false positives) and flags calls that
`aion_core/util.py` already solves: UTC timestamps, id generation, sha256
hashing, atomic file writes, JSON read/write. A flag is a lead, not a
verdict — a bridge script that deliberately avoids importing `aion_core`, or
a test fixture that needs the raw stdlib shape, is a legitimate reason to
keep what's there. Read the line before changing it.

This deliberately checks one thing well rather than everything shallowly.
It is not a general linter, and it is not trying to be.

## What this is not for

**Never smaller at the cost of correctness.** Validation, error handling,
security checks, evidence requirements (`tasks.complete` needs real
evidence — `aion_core/tasks.py`), audit logging, and tests are not the parts
to cut. If a "simpler" version silently drops one of these, it is not
simpler, it is a different, worse task wearing a smaller diff.

**Never a reason to skip understanding the problem.** The ladder starts
after you know what's actually required, not before. Guessing at a minimal
fix for a requirement you haven't confirmed produces confident, wrong code
faster than a careful one would.

**Never a reason to leave a genuinely necessary abstraction unbuilt.** If a
task has three real, current call sites needing the same behavior with
different inputs, that is not speculative — build the shared version. The
target is unearned complexity, not all complexity.

## Marking a deliberate shortcut

When a smaller solution trades something away on purpose — skips a corner
case that genuinely cannot occur here, hardcodes a value that is only ever
one thing in this system — say so in a comment at the decision point, not
in a commit message nobody will read at the call site. A future reader
should never have to reverse-engineer whether an omission was a choice.

## When this overlaps with learnrepo

`.claude/skills/learnrepo/` decides whether to bring in *external* code.
This skill decides whether new code needs to be written *at all*, and if
so, how little of it can satisfy the actual requirement. Use `learnrepo`
first if the requirement might already exist as a well-maintained external
tool; use `smallest-fix` for everything that ends up getting written,
including the adapter code `learnrepo` itself recommends.
