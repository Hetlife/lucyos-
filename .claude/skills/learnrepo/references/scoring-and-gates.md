# Scoring, gates and the validation matrix

## Why eight scores instead of one

A single "confidence: 85%" hides the thing you need to know. A candidate can
be a perfect functional fit with an unreadable license, or impeccably licensed
and unmaintained since 2021. Separate scores force the weakness to show.

| Score | What it measures | What lowers it |
|---|---|---|
| `evidence` | How much you actually verified, versus assumed | Few sources, no primary sources, no independent corroboration |
| `functional_fit` | Does it do the needed job | Partial coverage, needs significant glue |
| `lucyos_compatibility` | Fits LucyOS architecture, runtime, dependency policy | New runtime dependencies, conflicting concurrency model, Python version conflicts |
| `security` | Confidence the component is safe *in the intended use* | Unreviewed binaries, broad permissions, weak maintainer security response |
| `license` | Confidence the license permits the intended use | Unclear terms, mixed licensing, re-licensing history |
| `test` | Confidence the change is actually verified | Mocked or skipped tests, untested failure paths, different environment |
| `maintainability` | Cost of living with this for years | Bus factor of one, no releases, heavy patch divergence |
| `overall` | Honest summary — not an average | Any single weak dimension should pull it down |

Every score needs a one-line reason in `confidence_reasons`. A score without a
reason is a number someone made up, and it will be treated that way in review.

Scores are **not** an average and **cannot** outvote a blocking finding. One
unresolved critical security finding means not eligible, regardless of seven
scores of 99.

## Calibration

Aim for honest, not flattering:

- **95–100** — verified directly, multiple independent confirmations, tested
  in a LucyOS-equivalent environment.
- **85–94** — good primary evidence, minor gaps you can name.
- **70–84** — plausible, partly verified, real unknowns remain.
- **50–69** — mostly inference; you would not bet the system on it.
- **Below 50** — you are guessing. Say so, and go get evidence instead.
- **null** — not assessed. The gate treats this as blocking, which is correct:
  unknown is not the same as fine.

## Thresholds for requesting merge approval

The gate enforces these deterministically:

```bash
python3 .claude/skills/learnrepo/scripts/gate.py <investigation>/manifest.json --write <investigation>/gate.json
```

Blocking conditions — all must be clear:

- provenance verified, with an exact commit/tag/version recorded
- no `critical` or `high` security finding left `open`
- security screening recorded; no execution without recorded containment
- license identified, read from a stated source of truth, marked compatible,
  not requiring specialist legal review
- at least one test recorded, and **every** recorded test result is `pass`
- LucyOS regression suite run, result `pass`
- rollback steps recorded **and** tested
- `lucyos_compatibility` ≥ 90 · `security` ≥ 90 · `license` ≥ 90 ·
  `test` ≥ 95 · `overall` ≥ 90
- if an external service is required, activation is marked as a separate
  approval

Passing the gate permits exactly one thing: **asking the owner for approval.**
It is not approval, not a merge, and not a safety guarantee.

## Assessment fields

Alongside the scores, record:

- `expected_value`: low / medium / high / very_high
- `integration_effort`: low / medium / high
- `failure_impact`: low / medium / high / critical
- `reversibility`: easy / moderate / difficult
- `recommendation`: reject · research_only · reimplement_pattern ·
  wrap_dependency · prototype · prepare_integration · postpone ·
  ready_for_merge_approval

A high-value, high-effort, difficult-to-reverse change deserves more scrutiny
than its scores alone suggest. Say that in the report rather than letting the
numbers speak for themselves.

## Validation matrix

Derive tests from the capability contract before declaring anything works.
Cover what applies:

**Function** — happy path; boundary values; invalid, missing and adversarial
input; malformed responses from the dependency.

**Failure** — network or service unavailable; timeout; rate limit; partial
failure mid-operation; dependency returning hostile data; permission denied;
missing credentials.

**State** — restart and recovery; idempotency (running twice does not double
the effect); concurrent invocation.

**Isolation** — one project cannot reach another project's data; secrets do
not appear in logs, reports or error messages; the component cannot exceed its
declared permissions.

**Compatibility** — existing LucyOS behaviour unchanged; the runtime versions
LucyOS actually supports (Python 3.9+, standard library only); the regression
suite still passes.

**Operations** — resource ceilings under load; performance against the
baseline; feature flag off means genuinely inert; uninstall/rollback returns
the system to its prior state; the audit log records what it should.

**Interface** — if a UI is added, does it make the operator's decision
clearer, or is it decoration? Check the accessibility basics.

## Recording results honestly

Use the real result value: `pass`, `fail`, `skipped`, `mocked`, `flaky`,
`not_run`, `error`.

A test that was skipped is not a pass. A test whose dependency was mocked so
thoroughly that nothing real executed is not a pass. A test that passes three
times in five is `flaky`, and flaky means unknown. The gate treats anything
other than `pass` as blocking, which is the point — it removes the temptation
to round up.

If full validation was impossible in this environment, say exactly which parts
were not run and why, and do not claim merge readiness.
