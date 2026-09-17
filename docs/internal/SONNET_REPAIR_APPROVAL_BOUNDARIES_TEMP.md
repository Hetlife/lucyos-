# Sonnet Repair Approval Boundaries

This file supplements `docs/internal/LUCYOS_REPO_HEALTH_AUDITOR_TEMP.md` and applies to every Sonnet repair task generated from the LucyOS health audit.

## Critical Access Constraint — Repo Only

Sonnet has access **only to the LucyOS repository and the Git/GitHub-visible state available through that repository connection**.

Sonnet cannot inspect, read, execute against, or verify anything on the user's local PC, Mark-2 machine, OpenClaw host, Linux filesystem, local services, local databases, local logs, local environment variables, locally uncommitted files, or other machine state unless that evidence has first been deliberately sanitized and committed into the LucyOS repository by an authorized higher-level workflow.

Therefore every Sonnet repair task must be fully repo-self-contained.

Opus/high-reasoning planning must package into the repository everything Sonnet needs to execute safely, including as applicable:

- exact repo branch/ref and expected base SHA;
- relevant source paths;
- verified root-cause evidence;
- relevant CI/GitHub evidence;
- exact expected behavior;
- allowed files;
- protected files and boundaries;
- deterministic implementation instructions;
- test commands that can run in Sonnet's available repo environment;
- acceptance criteria;
- stop/escalation conditions;
- expected target branch for commits/pushes.

Do not instruct Sonnet to:

- inspect the local PC;
- inspect OpenClaw live state directly;
- read `/tmp`, `/home`, service logs, systemd runtime state, launchd runtime state, local SQLite databases, local secrets, local config files, or machine-only paths;
- compare against uncommitted local changes it cannot see;
- execute machine-level deployment or service-management checks unless a future explicitly authorized tool gives Sonnet that access;
- infer local runtime health from absence of repo evidence.

If a repair depends on local-machine evidence, Opus must classify that requirement as **BLOCKED / EXTERNAL EVIDENCE REQUIRED** and create a separate owner or machine-agent collection task. Sonnet must not guess.

## Principle

Sonnet may execute bounded, reversible, well-specified repairs autonomously only when the change stays inside the approved task scope and does not cross a protected decision boundary.

The high-reasoning model remains responsible for architecture, ambiguous root-cause decisions, security-sensitive behavior, authority policy, persistence/schema decisions, merge reconciliation, and final verification.

## Approval Levels

### LEVEL A — AUTO-APPROVED SONNET REPAIR

Sonnet may implement without asking for additional approval when ALL of the following are true:

- root cause has already been verified by the high-reasoning audit;
- all required evidence is available inside the repository/GitHub-visible state;
- task has explicit allowed files and acceptance criteria;
- change is local to the repository, reversible, and low-risk;
- no protected path is touched;
- no public/external interface contract changes;
- no database or persistence schema changes;
- no authority, approval, security, payment, trading, production, credential, or destructive-action logic changes;
- no new external dependency is introduced;
- no branch-history rewrite is required;
- tests clearly define the expected behavior;
- task does not require choosing between competing architectural approaches.

Examples:

- narrow bug fix in an already-defined implementation;
- adding or correcting a regression test;
- fixing an import/path/config typo inside the repo;
- deterministic cleanup of verified duplicate code where canonical implementation is already established;
- documentation sync after verified code behavior;
- small compatibility fix that preserves existing interfaces.

### LEVEL B — SONNET MAY PREPARE, OPUS MUST APPROVE BEFORE MERGE/PUSH

Sonnet may implement on a repair branch and run repo-available tests, but must STOP before final merge or canonical push when ANY of these apply:

- multiple core files or subsystems are modified;
- behavior changes across a subsystem boundary;
- a migration is involved but schema intent is already specified;
- task changes retry/recovery/failsafe behavior;
- task changes model-routing or delegation behavior;
- task changes deployment definitions, systemd files, launchd files, startup definitions, or runtime orchestration code (without claiming to verify the actual local service state);
- task changes a shared interface used by several modules;
- task requires non-trivial conflict resolution;
- task repairs failed commit/merge history where patch equivalence must be confirmed;
- full-suite regressions appear even if task-specific tests pass.

Required action: Sonnet produces the diff, repo-test evidence, risk summary, and commit SHA if committed to a repair branch. Opus reviews before merge/promotion.

### LEVEL C — STOP FOR HIGH-MODEL APPROVAL BEFORE CODE CHANGES

Sonnet must NOT modify code until Opus/high-reasoning review explicitly approves the approach when ANY of these apply:

- architecture or module ownership is unclear;
- root cause is uncertain or there are multiple plausible causes;
- required evidence exists only on a local machine Sonnet cannot access;
- task would alter authority/approval hierarchy;
- task touches `.lucy/authority/**`, protected-path policy, or equivalent governance controls;
- task weakens, bypasses, disables, or changes a safety/security gate;
- task changes authentication, credentials, secret handling, permissions, or trust boundaries;
- task changes persistence schema, canonical state format, migration strategy, backup/restore semantics, or data-loss behavior;
- task affects real-money, trading, payments, production deployment, account creation, signing, destructive actions, or external side effects;
- task introduces a new dependency, package, binary, service, or downloaded code;
- task requires deleting a substantial module or replacing the canonical implementation;
- task requires deciding which competing implementation should become canonical;
- task changes public API/CLI/protocol contracts;
- task requires force-push, history rewrite, branch deletion, or bypassing protections;
- task requires broad refactoring to make a local bug disappear.

Required action: stop, document repo-visible evidence and options, and escalate to Opus. Do not improvise.

### LEVEL D — OWNER APPROVAL REQUIRED

Sonnet and Opus must stop and request owner approval before actions that create material external, irreversible, financial, or privileged effects, including:

- push/merge directly to protected `main` when not already covered by an approved workflow;
- force-push or history rewrite;
- deleting important branches/tags/releases;
- changing repository protection or required checks;
- rotating/revoking credentials or changing external accounts;
- enabling production deployment;
- enabling real-money/trading/payment actions;
- purchasing or enabling paid services;
- destructive data migration or irreversible deletion;
- weakening security/authority policy for operational convenience.

## Sonnet Task Card Requirement

Every Sonnet task generated by Opus must include:

- `Approval level: A / B / C / D`
- `Repo-only: YES`
- `Base branch/ref`
- `Expected base SHA`
- `Why this level applies`
- `Evidence available in repo`
- `Allowed autonomous actions`
- `Actions requiring Opus review`
- `Actions requiring owner approval`
- `Stop conditions`

If the task changes during execution and crosses into a higher approval level, Sonnet must immediately adopt the stricter level and stop at the relevant boundary.

If the task requires information that is not present in the repo, Sonnet must report `BLOCKED — REQUIRED EVIDENCE NOT AVAILABLE IN REPO` and identify the exact missing evidence. It must not invent or infer machine state.

## Commit and Push Boundary

Sonnet may create ordinary task commits on an explicitly approved repair branch when the task is Level A or Level B and repo-available tests pass.

Sonnet may push to that repair branch only when the task instructions explicitly permit it.

Sonnet must never assume that permission to edit code also implies permission to merge or push to a canonical/protected branch.

Before any final push task, using only repo/GitHub-visible information, Sonnet must:

1. fetch remote state;
2. confirm target branch and remote HEAD;
3. verify ancestry and divergence;
4. inspect full repo diff;
5. confirm every changed file maps to approved task IDs;
6. run required repo-available targeted and full-suite checks;
7. confirm no secrets or unrelated generated files are included;
8. confirm no protected boundary was crossed;
9. stop if remote HEAD changed unexpectedly or conflicts are ambiguous.

Sonnet must not claim that local-PC services, processes, files, databases, OpenClaw runtime, or deployment health were verified unless such evidence was explicitly committed into the repo by an authorized process.

Final canonical merge/promotion requires Opus verification, and owner approval where Level D applies.

## Default Rule

When uncertain, do not guess the approval level downward.

Escalate to the stricter boundary and report exactly what changed, why the current task can no longer proceed autonomously, and what decision or repo-contained evidence is needed.
