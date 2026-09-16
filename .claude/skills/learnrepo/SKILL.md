---
name: learnrepo
description: Evidence-based capability acquisition for LucyOS — research, verify, security-screen, license-check, and safely adapt (or reject) external repositories, packages, plugins, and reference implementations. Use this skill whenever the user supplies a GitHub or Git URL, package name, paper, demo, or reference implementation; asks LucyOS to learn or add a capability, adapter, plugin, integration, automation, workflow, UI artifact, or agent feature; asks to find the best existing solution for a capability; or asks whether an external project is worth using, safe, maintained, or license-compatible. Use it before adopting any new third-party dependency, even when the user does not mention security or licensing. It never merges, deploys, activates external services, or executes untrusted code without explicit owner approval.
---

# learnrepo — capability acquisition for LucyOS

LucyOS gains capabilities from the open-source world without importing other
people's risk. This skill is the disciplined path from "here's a repo" to
"LucyOS can do this, safely, and we can undo it."

It is **not** a repository importer. Most investigations should end in
something smaller than a merge: a wrapped dependency, a narrow adapter, an
independently-written pattern, a research note, or a clear rejection.

## The one rule that is never negotiable

**You prepare. The owner merges.** Never merge to a protected branch, deploy,
enable a capability in production, activate an external account, or accept a
license obligation on the owner's behalf. Preparing a perfect, fully-passing
change set still ends with an approval request. Silence is not approval, and a
general instruction to "work autonomously" is not merge approval.

In LucyOS band terms (`docs/architect/03_THREAT_MODEL_AND_SECURITY.md` §3),
everything this skill does autonomously is GREEN. The merge itself is RED.

## Pipeline

```
UNDERSTAND → DISCOVER → VERIFY → INSPECT → COMPARE → DECIDE
→ DESIGN → ISOLATE → ADAPT → TEST → REPORT → APPROVAL → (owner merges) → MONITOR
```

Work the stages in order. Skipping ahead is how unsafe code gets executed and
how license problems get discovered after the fact. It is always acceptable to
stop early with "not worth it" — that is a successful outcome, not a failure.

### 1. UNDERSTAND

Restate the capability in LucyOS terms before looking at any repository. What
would LucyOS actually be able to do afterwards? Which projects consume it
(LucyOS core, Strategy Factory, SEVAACONNECT, a future project)? What is the
smallest version of this that would be useful?

Set up the workspace — this creates the artifact tree outside the repo:

```bash
python3 .claude/skills/learnrepo/scripts/learnrepo.py new <capability-id>
```

Capability IDs are stable, lowercase, dash-separated, and path-independent
(`live-agent-activity-view`, not `ui/dashboard/v2`). They outlive directory
layouts.

### 2. DISCOVER

If the user named a repository, still look for at least one alternative and
for the possibility that LucyOS needs nothing new. If they did not, find
several plausible candidates.

Never rank by stars or downloads. Popularity measures attention, not
trustworthiness, fit, or maintenance. A 200-star library maintained by a
responsive author often beats a 40k-star framework in maintenance mode.

### 3. VERIFY (provenance before anything else)

Resolve the canonical owner, URL, and the **exact commit or tag** you are
evaluating. Everything downstream — license, security, tests — is a claim
about that exact revision, not about the project's reputation.

Watch for impersonation, recent ownership transfer, a sudden maintainer
change, or a package name that is one character from a popular one.

### 4. INSPECT

Read `references/security-screening.md` and work its checklist.

**Default: do not execute candidate code.** Static reading plus dependency and
history review answers most questions. If you believe execution is genuinely
required, first run:

```bash
python3 .claude/skills/learnrepo/scripts/sandbox_probe.py
```

It reports what containment this host actually has. If it reports no usable
containment, do not execute — say so in the report and continue with static
analysis. Never substitute optimism for a sandbox, and never describe a
containment method the probe did not confirm.

Run the repeatable static checks rather than reading everything by hand:

```bash
python3 .claude/skills/learnrepo/scripts/static_screen.py <quarantine-dir> --json
```

It flags install hooks, dynamic evaluation, network calls, credential access,
persistence, obfuscation, binaries, and committed secrets. Treat it as a
*lead generator*: confirm every material finding by reading the actual code in
context, and remember a clean report is not proof of safety.

### 5. COMPARE

With two or more viable candidates, build an honest comparison across
functional fit, LucyOS architectural fit, maintenance and bus factor,
release discipline, security responsiveness, documentation and tests,
dependency weight, performance, privacy, integration cost, license, and
reversibility. Do not shape the comparison around a preferred answer.

Keep four categories visibly separate throughout: **facts** (observed in the
repository or a primary source), **maintainer claims** (README/docs), **user
reports** (issues, discussions, reviews), and **your inference**. Most bad
adoption decisions come from an inference quietly promoted to a fact.

### 6. DECIDE

Read `references/scoring-and-gates.md`. Score the eight dimensions with a
one-line evidence reason each, then let the script decide eligibility:

```bash
python3 .claude/skills/learnrepo/scripts/gate.py <investigation-dir>/manifest.json
```

The gate is deterministic on purpose. A model that eyeballs "is 88 close
enough to 90" will eventually talk itself into a yes. A blocking security or
license finding overrides every high score — that is not an average, it is a
veto.

Valid outcomes, roughly in order of how often they should be chosen:
reject · research-only · reimplement-pattern · wrap-dependency ·
build-adapter · postpone · prepare-integration.

### 7. DESIGN

Read `references/lucyos-integration.md`. Prefer, in order: LucyOS interface +
isolated adapter → plugin with a capability contract → sidecar behind a narrow
authenticated interface → vendored component → core modification (last resort).

Do not duplicate LucyOS core services inside a project. Identity, secrets,
approvals, logging, memory, scheduling, messaging, and policy belong to LucyOS
centrally. Strategy Factory and future systems are LucyOS-governed projects,
not independent platforms with their own parallel infrastructure.

### 8. ISOLATE

Work on a feature branch or worktree, never on `main`. Record the baseline
LucyOS commit and the candidate commit in the manifest. Keep quarantined
third-party source in the artifact tree (outside the repo) — do not commit a
cloned repository into LucyOS for analysis.

### 9. ADAPT

Make the smallest coherent change. Pin versions. Deny by default. Keep secrets
out of source and logs. Disable optional telemetry. Add a feature flag that
defaults to off. Wrap the dependency behind a LucyOS-owned interface so it can
be replaced later without touching callers.

LucyOS runs on the Python standard library only (`README.md`). Adding a
third-party runtime dependency to LucyOS core is a significant architectural
change, not a detail — justify it explicitly or design around it.

If you patch an external component: state the original defect, list every
patched file, add a regression test, note whether it should go upstream, and
record the ongoing maintenance burden. Never present a patched component as
"now safe" overall — you fixed one thing you found.

### 10. TEST

Read `references/scoring-and-gates.md` for the validation matrix. Test the
capability contract, not the happy path alone: adversarial input, unavailable
network, timeouts, missing credentials, restart and idempotency, project
isolation, secret containment, resource ceilings, feature-flag off, and the
rollback path.

Run the existing LucyOS regression suite as well:

```bash
python3 -m unittest discover -s tests -t . -q && ./aion scan .
```

Label skipped, mocked, flaky, or differently-environed tests accurately. A
test that did not really run is not a pass, and recording it as one destroys
the value of the whole exercise.

### 11. REPORT

```bash
python3 .claude/skills/learnrepo/scripts/render_report.py <investigation-dir>
```

This renders the 16-section decision report from the manifest and gate result.
See `references/report-template.md`. Summarize; link to evidence rather than
pasting logs. Never put secrets, tokens, private data, or internal hostnames
in a report — reports get shared.

### 12. APPROVAL

Present the report and ask one precise question, for example:

> Approve merging capability `live-agent-activity-view` from branch
> `feature/learnrepo-live-view` into `main` at tested commit `abc1234`?
> This adds a read-only activity panel behind a feature flag defaulting to
> off. No production deployment or external account activation is included.

Optionally record it in AION so the decision is auditable and survives the
conversation:

```bash
./aion approval-add "merge capability <id> into main at <commit>" \
  --why "<one line>" --cost "none" --reversibility "easy: revert commit, flag off" \
  --prepared "branch tested, gate PASS" --resumes "merge and enable flag"
```

### 13. MONITOR

After an approved integration, register the upstream source in the registry.
Never auto-pull upstream changes — every update is a new evaluation at a new
commit. Notify the owner only when there is an advisory, a breaking change, a
license change, an ownership change, or a genuinely valuable new capability.

## Reference files

| File | Read it when |
|---|---|
| `references/security-screening.md` | INSPECT — the layered check list and what each finding means |
| `references/license-gate.md` | Any licensing question, before copying or vendoring anything |
| `references/scoring-and-gates.md` | DECIDE and TEST — score definitions, thresholds, validation matrix |
| `references/manifest-schema.md` | Writing or validating a manifest |
| `references/report-template.md` | REPORT — the 16 sections and tone |
| `references/lucyos-integration.md` | DESIGN — integration patterns and capability contract |
| `references/examples.md` | Seven worked scenarios including unclear licenses and WhatsApp-style external services |

## Scripts

All scripts are Python 3.9+ standard library only, matching LucyOS's
zero-dependency policy. None of them execute candidate code.

| Script | Purpose |
|---|---|
| `scripts/learnrepo.py` | Create and inspect the artifact tree; `new`, `list`, `show`, `paths` |
| `scripts/sandbox_probe.py` | Report what containment this host actually has |
| `scripts/static_screen.py` | Non-executing static risk scan of a quarantined candidate |
| `scripts/validate_manifest.py` | Validate a manifest against schema v1 |
| `scripts/gate.py` | Deterministic merge-eligibility decision |
| `scripts/render_report.py` | Render the 16-section report from manifest + gate |

## Install and invoke

The skill lives at `.claude/skills/learnrepo/` and is discovered
automatically when working inside this repository. To make it available
everywhere, copy the directory to `~/.claude/skills/learnrepo/`.

Invoke it by asking for the work in normal language — "is this repo worth
using?", "find the best way to add X", "can LucyOS learn this?" — or by naming
the skill. Version history and deliberate deviations from the original build
specification are in `CHANGELOG.md`.

A good first request, which integrates nothing and executes nothing:

> Use learnrepo to research and compare repositories that could add a visual
> live-agent activity interface to LucyOS. Do not integrate or execute
> untrusted code. Produce the candidate comparison, security and license
> assessment, LucyOS-native integration design, confidence scores, and a
> prototype plan.

## Where things live

Skill files are source and live in the repo. Investigation artifacts are
machine state and live under `$AION_HOME/learnrepo/` (default
`~/openclaw/shared_brain/learnrepo/`), outside version control — the same rule
LucyOS already applies to the shared brain. This keeps third-party evidence,
quarantined clones, and research notes out of a repository that may be public.

Run `python3 .claude/skills/learnrepo/scripts/learnrepo.py paths` to see the
resolved locations on this machine.

## Honesty requirements

These exist because the failure mode that actually hurts LucyOS is not "the
integration broke" — it is "the report said it was fine."

- Never claim 100% safety, universal compatibility, or that software "works
  100%". State what was tested, in which environment, and what remains unknown.
- Never present a scanner result as a verdict, or a clean scan as proof.
- Never hide a finding because you patched it.
- Never fabricate sources, dates, scan output, test results, or approvals.
- If evidence is thin, lower the confidence score and say why. A low score
  with a clear reason is far more useful than a confident guess.
