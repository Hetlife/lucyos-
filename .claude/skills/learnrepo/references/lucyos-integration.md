# LucyOS integration policy

## The governing idea

LucyOS is the operating and integration layer. Strategy Factory, SEVAACONNECT
and anything built later are **projects governed by LucyOS**, not independent
platforms that happen to sit nearby.

The practical consequence: a project must not grow its own identity, secrets,
approvals, logging, memory, scheduling, messaging, observability or policy
enforcement. Those are LucyOS services. Every duplicate is another place a
credential can leak, another audit trail that disagrees with the real one, and
another system to migrate later.

When a candidate repository brings its own versions of these — its own user
store, its own secret handling, its own scheduler — that is an architectural
cost, not a feature. Weigh it in `lucyos_compatibility`.

## What LucyOS actually is today

Verify against the repository rather than trusting this summary, but as of
schema v1:

- `aion_core/` is the deterministic kernel: tasks, approvals, router, model
  routing, budget governor, worker loop, memory, health, backups.
- **SQLite under `AION_HOME` is canonical state.** Markdown surfaces are
  generated views. Never introduce a second source of truth.
- **Python standard library only.** `README.md` states this explicitly. Adding
  a runtime dependency to LucyOS core is an architectural decision requiring
  justification, not an implementation detail.
- Execution is argv-based and allowlisted (`aion_core/worker.py`); there is no
  shell. Anything that needs shell semantics will not fit without a change to
  the security boundary — which is owner territory.
- Task completion requires evidence. Approvals are typed objects. Bands are
  GREEN / AMBER / RED (`docs/architect/03_THREAT_MODEL_AND_SECURITY.md`).
- Artifacts, evidence and machine state live under `AION_HOME`, never in git.

## Integration patterns, in order of preference

**1. LucyOS interface + isolated adapter.** Define the interface LucyOS wants,
then write a thin adapter that satisfies it using the dependency. Callers
depend on the interface. Replacing the dependency later touches one file.
Prefer this.

**2. Plugin with an explicit capability contract.** For optional capabilities
with a stable contract and a registration point.

**3. Sidecar behind a narrow authenticated interface.** When the component
needs a different runtime, heavy dependencies, or stronger isolation. Bind to
loopback, authenticate, keep secrets on the LucyOS side.

**4. Vendored component.** Only when license-compatible, small, and pinned by
checksum. You now own maintenance and security updates for it.

**5. Direct core modification.** Last resort. Requires a clear argument that no
modular alternative exists, plus tests and a rollback.

## The capability contract

Every integration defines these before code is written. If you cannot answer
one, that is the next research question, not an omission to paper over.

- **Capability ID** — stable, path-independent (`live-agent-activity-view`).
- **Inputs / outputs / error behaviour** — including what happens on partial
  failure.
- **Permissions and data access** — least privilege, deny by default.
- **Network behaviour** — destinations, when, and whether optional.
- **Secrets** — which are needed and where they stay (never in source, logs,
  reports, prompts or the artifact tree).
- **Resource limits** — CPU, memory, disk, time, token and money ceilings.
- **Observability** — health check, structured logs with no sensitive content,
  what an operator sees when it breaks.
- **Feature flag** — name, and a default of off.
- **Failure isolation and fallback** — LucyOS keeps working when this fails.
- **Version pinning and update policy** — pinned, with updates re-evaluated.
- **Test ownership** — which tests prove it still works.
- **Rollback / uninstall path** — tested, not assumed.
- **Consumers** — which projects may use it.

## Structure that survives reorganisation

Today's directory layout is not permanent, so do not encode it:

- Identify capabilities by ID, not by path.
- Version every schema (`schema_version`) and provide a migration when it
  changes rather than editing records in place.
- No absolute paths in code or manifests; resolve from `AION_HOME` or the
  repository root.
- No cross-project imports. Projects talk through LucyOS interfaces.
- Keep source evidence, analysis, integration code and runtime configuration
  separate — they have different lifetimes and different audiences.

## Where artifacts live, and why it matters here

Skill files are source and live in the repository. Investigation artifacts —
research notes, quarantined clones, assessments, manifests, reports — live
under `$AION_HOME/learnrepo/`, outside version control.

This is not tidiness. The LucyOS repositories are currently **public**
(`docs/architect/01_CURRENT_STATE_AUDIT.md`). Committing third-party evidence,
internal assessments and quarantined source into a public repository would
publish both the analysis and, potentially, someone else's code under terms
that may not allow it.

## Bands

Map every action to a band before doing it:

- **GREEN** — read-only inspection, research, static analysis, writing
  adapters and tests on a feature branch, running the local test suite. All of
  learnrepo's autonomous work is GREEN.
- **AMBER** — actions with external effects inside a standing policy and
  budget. learnrepo does not create these on its own.
- **RED** — merging to a protected branch, deploying, enabling a capability in
  production, activating an external account, accepting a license obligation,
  spending money, changing a security boundary. Every one of these is an owner
  decision, requested explicitly and recorded.
