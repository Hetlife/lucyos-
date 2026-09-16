# Capability manifest — schema v1

The manifest is the durable record of an investigation: what was examined, at
which revision, what was found, what was decided, and how to undo it. Reports
are rendered from it, the gate reads it, and a future maintainer wanting to
know "why is this dependency here?" reads it.

Create one with `learnrepo.py new <capability-id>`; validate with
`validate_manifest.py`; evaluate with `gate.py`.

## Design rules

- **Unknown is null or empty, never a hopeful default.** A blank manifest must
  fail the gate, and it does. Optimistic defaults are how unreviewed things
  get merged.
- **`schema_version` is mandatory.** When the schema changes, bump it and ship
  a migration rather than editing old records in place.
- **Identifiers are path-independent.** `capability_id` is stable across any
  future reorganisation of LucyOS.
- **No secrets, ever.** Not in evidence, not in snippets, not in notes.

## Fields

### Identity
| Field | Type | Notes |
|---|---|---|
| `schema_version` | int | Currently `1` |
| `capability_id` | string | lowercase, dash-separated, stable |
| `name`, `purpose` | string | human-readable |
| `request` | string | the user's request, restated in LucyOS terms |
| `consumers` | string[] | which projects may use this |
| `status` | enum | draft · research · assessed · prepared · approved · integrated · rejected · postponed |
| `created_at`, `updated_at` | ISO-8601 UTC | |

### `candidates[]`
`{name, url, verdict, why}` — everything you seriously considered, including
the ones you rejected. A single-entry list is a weak comparison and the report
says so.

### `source`
`kind` · `canonical_url` · `owner` · `commit` · `tag` · `version` ·
`release_date` · `retrieved_at` · `provenance_verified` (bool) ·
`provenance_notes`.

At least one of commit/tag/version is required by the gate. Every other
finding is a claim about that revision.

### `license`
`spdx` · `source_of_truth` (which file, at which revision, you actually read) ·
`obligations[]` · `commercial_use` · `redistribution` · `network_use` ·
`modification` · `compatible_with_lucyos` (true/false/null) ·
`requires_legal_review` (bool) · `notes`.

See `license-gate.md`. The gate blocks unless the license is identified, has a
source of truth, is marked compatible, and does not require specialist review.

### `evidence[]`
`{claim, type, source, date, note}` where `type` is one of `fact`,
`maintainer_claim`, `user_report`, `tool_finding`, `inference`.

Keeping these separate is the single most useful discipline in the whole
schema. Most bad adoption decisions are an inference that was quietly filed as
a fact.

### `learned`, `disposition`
`learned` is prose: what LucyOS now understands. `disposition` records what
happened to the code: `reused` · `wrapped` · `rewritten` · `patched` ·
`rejected`, each a list of specifics.

### `dependencies`, `runtime`
`dependencies`: `direct[]` · `transitive_count` · `pinned` · `lockfile`.
`runtime`: `permissions[]` · `network[]` · `secrets[]` · `telemetry` ·
`data_flows[]`.

### `security`
`findings[]` of `{id, severity, title, evidence, disposition, confidence}` ·
`screened_at` · `screening_method` · `execution_performed` (bool) · `sandbox`.

Severity: critical · high · medium · low · info.
Disposition: open · patched · mitigated · accepted · rejected · false_positive.

Patched findings stay listed. The gate blocks on any open critical/high, and
on `execution_performed: true` with no recorded sandbox.

### `changes`, `tests`
`changes`: `files_added[]` · `files_changed[]` · `files_removed[]`.
`tests`: `suites[]` of `{name, command, result, notes}` ·
`regression_suite_run` (bool) · `regression_result`.

Result values: pass · fail · skipped · mocked · flaky · not_run · error. Only
`pass` passes.

### `resources`
`cpu` · `memory` · `disk` · `network` · `latency` · `token_cost` ·
`monetary_cost`. Fill what is material; empty is honest when not measured.

### `confidence` and `confidence_reasons`
Eight scores 0–100 or null, each with a reason. See `scoring-and-gates.md`.

### `assessment`
`expected_value` · `integration_effort` · `failure_impact` · `reversibility` ·
`recommendation`.

### `limitations[]`, `residual_risks[]`
What this does not do, and what could still go wrong after merge. An empty
`residual_risks` triggers a warning, because genuinely zero-risk changes are
rare enough to be worth questioning.

### `feature_flag`, `rollback`, `integration`
`feature_flag`: `{name, default}` — default `off`.
`rollback`: `{steps[], tested (bool), tested_evidence}` — the gate requires
both steps and a tested flag.
`integration`: `{pattern, branch, baseline_commit, target_branch}` where
pattern is adapter · plugin · sidecar · vendored · core.

### `external_services`
`required` · `services[]` · `accounts_needed[]` · `privacy_review_required` ·
`cost_review_required` · `activation_is_separate_approval`.

Anything needing an external account — messaging providers, telephony,
payment, customer contact — is flagged here. Account creation, consent and
privacy review, cost approval and activation are separate owner decisions and
are never bundled into a code merge.

### `monitoring`, `approval`
`monitoring`: `{enabled, watch[]}` — upstream sources to watch after an
approved integration. Updates are never auto-pulled; each is a new evaluation.
`approval`: `{status, approver, timestamp, note}` where status is
not_requested · requested · approved · denied. Only a human sets `approved`.

## Migrating

When schema v2 arrives: add `migrations/v1_to_v2.py`, bump `SCHEMA_VERSION`,
and keep the v1 validator able to recognise and reject v2 documents clearly
(it already reports a version mismatch rather than guessing). Never silently
reinterpret an old record under new rules.
