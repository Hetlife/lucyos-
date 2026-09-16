# learnrepo changelog

## 1.0.0 — 2026-09-16

First release. Prepared on branch `claude/lucyos-architecture-audit-4o4q83`,
not merged.

**Manifest schema: v1.** Future changes bump `SCHEMA_VERSION` in
`scripts/learnrepo_paths.py` and ship a migration rather than reinterpreting
existing records.

Added:

- `SKILL.md` — the UNDERSTAND → … → MONITOR pipeline and the non-negotiable
  "you prepare, the owner merges" rule.
- References for security screening, license gate, scoring and validation,
  manifest schema, report template, LucyOS integration policy, and seven
  worked scenarios.
- Scripts: workspace CLI, sandbox probe, non-executing static screen, manifest
  validator, deterministic merge gate, 16-section report renderer. Standard
  library only.
- `assets/example-passing-manifest.json` — a clearly-labelled synthetic
  fixture that satisfies the gate; also used by the tests.
- `tests/test_learnrepo_skill.py` in the LucyOS suite — 46 tests, weighted
  toward refusal paths.

Deliberate deviations from the build specification, with reasons:

- **No `agents/openai.yaml`.** The current skill format carries user-facing
  metadata in `SKILL.md` frontmatter; nothing loads a separate agent YAML, and
  the specification also forbids decorative or unused files. Shipping one
  would assert a compatibility that was never tested.
- **Artifacts live under `$AION_HOME/learnrepo/`, not in the repository.** The
  specification's directory layout is preserved logically, but the LucyOS
  repositories are currently public, and committing third-party evidence,
  assessments and quarantined clones into a public repository is a disclosure
  and licensing risk. The specification explicitly permits a safer native
  convention.
- **Execution of candidate code defaults to refused.** Docker is installed on
  the development host but its daemon is unreachable, so container sandboxing
  would have been a claim rather than a capability. `sandbox_probe.py` tests
  containment rather than assuming it, and the gate blocks any manifest
  reporting execution without recorded containment.
