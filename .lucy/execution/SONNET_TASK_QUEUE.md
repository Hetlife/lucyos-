# SONNET_TASK_QUEUE — LucyOS consolidation cycle 2026-09-16

Frozen by Fable. Executors: Sonnet (class B) unless stated. Base branch for every
task: `integration/consolidation-20260916`. Branch naming is mandatory:
`task/<TASK_ID>-<slug>`. One task per branch, one PR per task, PR targets the
integration branch. **Never merge.** The `authority-gate` CI job reads the
baseline from the integration branch; if your PR touches a protected path your
task does not have an override for, the gate fails and that is the correct
outcome — stop and escalate, do not edit gates.

Before starting any task, run on your branch: `python3 -m unittest discover -s tests -t . -q && ./aion scan .`
and confirm the VERIFIED START STATE below. Before opening the PR run the same,
plus `python3 scripts/verify_authority.py strict --base origin/integration/consolidation-20260916 --branch "$(git branch --show-current)"`
and `python3 scripts/verify_authority.py anti-dup --base origin/integration/consolidation-20260916`.

Commit message first line: `<TASK_ID>: <what changed>`. Include a `Task-ID: <TASK_ID>` trailer.

Ordering: S-01 is independent. S-02 → S-03 → S-04 are sequential (each starts
from the integration branch after the previous PR is merged by the owner).
S-05, S-07, S-08, S-09 are independent of each other and of S-02..S-04.

---

## S-01 — Skill-registry policy-class normalization + upgrade regression test

- PRIORITY: P0 (live Mark-2 registry is DEGRADED by this)
- OBJECTIVE: legacy lowercase policy classes heal on `ensure_defaults()`; a regression test proves an upgraded database validates clean.
- WHY: `validate_registry()` (`aion_core/skills.py:203-210`) is case-sensitive; `register()` uppercases on write but the compatibility migration (`skills.py:163-164`) only maps word labels. Pre-Q005 rows with `f0`/`e1`/`r1`/`internal`/`p1` stay invalid forever. Opus reproduced it; the Drive patch (`LUCYOS_STEP1_F0_MIGRATION_FIX.patch`) fixes only `f0`.
- VERIFIED START STATE: on integration branch, `python3 - <<'PY'` injecting `cost_class='e1'`, `risk_class='r1'`, `data_class='internal'` via SQL then `skills.ensure_defaults()` → `validate_registry()` returns 3 errors.
- ALLOWED FILES: `aion_core/skills.py`, `tests/test_skills.py`, `tests/test_migrations.py` (new)
- FORBIDDEN: everything else; in particular `aion_core/db.py` (the fix is in `ensure_defaults`, not the schema).
- EXACT ACTION:
  1. In `ensure_defaults()`, after the existing two word-label UPDATEs, add generic normalization for all four columns:
     `UPDATE skills SET cost_class=upper(cost_class) WHERE cost_class <> upper(cost_class)` and the same for `risk_class`, `data_class`, `priority`. Keep the word-label mappings (they must run first so `local`→`F0` still works).
  2. Create `tests/test_migrations.py` (class `TestUpgradeFromOldState(AionTest)`) with: (a) the lowercase-`f0` case from the Drive patch; (b) a case injecting all four columns lowercase across different skills, asserting `validate_registry() == []` after `ensure_defaults()`; (c) idempotency: calling `ensure_defaults()` twice yields identical rows.
  3. Add a module docstring to `tests/test_migrations.py` stating the owner rule: every schema/enum/policy migration ships with an upgrade-from-old-state test here.
- DEPENDENCIES: none
- MODEL CLASS: B
- TOKEN/COST BUDGET: ≤ 40k tokens
- TESTS: full suite; `python3 -m unittest tests.test_migrations -v`
- ACCEPTANCE: all three new tests pass; full suite passes; `./aion scan .` clean; no other file changed.
- FAILURE CONDITIONS: touching `db.py`; changing `COST_CLASSES` or any enum; loosening `validate_registry()`.
- ROLLBACK: revert the PR; no schema change involved.
- ESCALATE WHEN: a fourth normalization case appears that needs a schema change; any existing test breaks.
- EXPECTED OUTPUT: PR `S-01: normalize legacy policy classes; add upgrade-from-old-state test`.

## S-02 — Salvage `claude/lucyos-architecture-audit-4o4q83` (clean merge + archive its planning docs)

- PRIORITY: P1 (carries the argv-based execution boundary, a security hardening)
- OBJECTIVE: bring the code from that branch onto the integration branch; move its planning documents to an archive so there is one planning surface.
- WHY: `git merge-tree` proves the merge is conflict-free against Q006. Its `docs/architect/*` duplicates `.lucy/planning`+`.lucy/authority`+`.lucy/execution` (Opus brief §5.4).
- VERIFIED START STATE: `git merge-tree --write-tree origin/integration/consolidation-20260916 origin/claude/lucyos-architecture-audit-4o4q83` prints a tree id with no `CONFLICT` line.
- ALLOWED FILES: everything the merge brings, plus `.lucy/archive/docs-architect-20260916/**` (new). Protected-path override granted: `aion_core/worker.py`.
- FORBIDDEN: any edit to merged code beyond what the merge itself produces; `docs/architect/` must not survive at its original path.
- EXACT ACTION:
  1. `git merge --no-ff origin/claude/lucyos-architecture-audit-4o4q83` (merge commit message `S-02: salvage argv execution boundary, util.ago, recall foundation, dev skills`).
  2. `git mv docs/architect .lucy/archive/docs-architect-20260916` and add `.lucy/archive/README.md` (3 lines: archived planning material; superseded by `.lucy/`; do not resume from here).
  3. Run the full suite, `./aion scan .`, both verifier modes.
- DEPENDENCIES: none (do this before S-03)
- MODEL CLASS: B
- TOKEN/COST BUDGET: ≤ 30k tokens
- TESTS: full suite (expect the count to rise: the branch adds tests)
- ACCEPTANCE: suite passes; anti-dup passes (`recall` and `.claude/skills` are allowlisted/unprotected); `docs/architect/` absent; strict gate passes with S-02 override.
- FAILURE CONDITIONS: any conflict marker; any test skipped; editing `worker.py` beyond the merge result.
- ROLLBACK: revert the merge commit.
- ESCALATE WHEN: merge-tree shows a conflict (integration moved); anti-dup flags anything.
- EXPECTED OUTPUT: PR with one merge commit + one relocation commit.

## S-03 — Salvage `feature/resource-governor` with the `research_registry` rename

- PRIORITY: P1
- OBJECTIVE: land the capacity governor, flag-gated OFF, without the module-name collision.
- WHY: Fable decision D2/D3 (execution package §4, §8). The 78-line `aion_core/learnrepo.py` on that branch is a third-party research registry, unrelated to Q006's `learnrepo.py`.
- VERIFIED START STATE: `git merge-tree --write-tree origin/integration/consolidation-20260916 origin/feature/resource-governor` reports CONFLICT in `aion_core/cli.py`, `aion_core/db.py`, `aion_core/health.py`, `aion_core/learnrepo.py` (add/add).
- ALLOWED FILES: everything the cherry-pick brings; `aion_core/research_registry.py` (new, = the branch's 78-line file); `aion_core/resource_governor/**`; `aion_core/cli.py`; `aion_core/health.py`; `aion_core/bootstrap.py`; `tests/test_resource_governor_*.py`; `tests/test_research_registry.py` (new, if the branch had tests for the registry, move them). Protected overrides granted: `aion_core/db.py`, `aion_core/worker.py`, `aion_core/resume.py`, `aion_core/router.py`, `.secretscanignore`.
- FORBIDDEN: changing any default flag value (admission must stay OFF); changing Q006's `learnrepo.py` semantics; adding tables outside `db.py`.
- EXACT ACTION:
  1. `git cherry-pick -x 1d6aa7ef67f77a381a3591933f356113e029753e` (expect conflicts).
  2. `cli.py`, `db.py`, `health.py`: both sides are additive; keep both hunks, Q006's first. In `db.py` the new tables `resource_snapshots`, `research_targets` go after Q006's `learnrepo_*` tables.
  3. `aion_core/learnrepo.py` add/add: keep OURS (Q006, 669 lines). Write THEIRS (78 lines) to `aion_core/research_registry.py`, changing only the module docstring's first line to `"""Research registry — third-party candidates move through RESEARCH → … → APPROVED."""`.
  4. Update every import of the registry on the branch's side to `research_registry`: `aion_core/resource_governor/__init__.py`, `capability_gate.py`, `providers/__init__.py` (docstring), `bootstrap.py:144`, and the `cli.py` `resource-governor learnrepo` sub-op (rename the sub-op to `research`). Q006's `learnrepo` imports stay untouched.
  5. Confirm `_resource_governor_gate` in `worker.py` still reads `resource_governor.flags.flag("resource_governor.enforce_admission")` and that the default is False (`grep -n enforce_admission aion_core/resource_governor/flags.py`).
  6. Full suite, scan, both verifier modes.
- DEPENDENCIES: S-02 merged
- MODEL CLASS: B
- TOKEN/COST BUDGET: ≤ 80k tokens
- TESTS: full suite; `tests/test_resource_governor_*`; an added test asserting `resource_governor.flags.flag("resource_governor.enforce_admission") is False` on a fresh home.
- ACCEPTANCE: no file named `learnrepo` changes meaning; `python3 -c "import aion_core.research_registry, aion_core.learnrepo"` works; suite passes; anti-dup passes; strict passes with S-03 override; `./aion boot` on a fresh home shows the `resource_governor` step with `enabled: False` or equivalent.
- FAILURE CONDITIONS: any `CREATE TABLE` outside `db.py`; any new `sqlite3.connect`; admission flag default changed; a conflict resolved by dropping either side's code.
- ROLLBACK: revert the PR (tables are additive; older code ignores them).
- ESCALATE WHEN: anti-dup flags a file inside `resource_governor/` for a reason other than the name; the branch's registry tests depend on a `learnrepo` CLI surface Q006 also defines.
- EXPECTED OUTPUT: PR `S-03: land resource governor (flag OFF) as research_registry + resource_governor`.

## S-04 — Governor precedence: most-restrictive-wins, enforced and tested

- PRIORITY: P1
- OBJECTIVE: make Fable decision D3 machine-checked: the capacity gate may lower a task's model class or skip it; it may never raise a class the spend governor already lowered.
- WHY: two governors on different axes; without a rule, precedence is whatever the code happens to do.
- VERIFIED START STATE: S-03 merged; `worker._resource_governor_gate` returns `class_override` from `resource_governor.admission.apply`.
- ALLOWED FILES: `aion_core/worker.py` (override granted, only inside `_resource_governor_gate`), `aion_core/resource_governor/admission.py`, `tests/test_governor_precedence.py` (new)
- FORBIDDEN: `aion_core/governor.py`; any change to POLICY tables.
- EXACT ACTION: in `_resource_governor_gate`, clamp: if `class_override` ranks higher than `cls` on the order `DET < A < B < C < D` (use `agents.py`'s ordering; do not define a new one), ignore the override and record a note `"capacity gate attempted upgrade; refused"`. Test: with the flag forced on in-test, a decision proposing `C` for a task already at `B` results in `B`; a decision proposing `A` results in `A`; a `skip` still skips.
- DEPENDENCIES: S-03
- MODEL CLASS: B
- TOKEN/COST BUDGET: ≤ 30k tokens
- TESTS: new file + full suite
- ACCEPTANCE: three assertions above; suite passes; strict passes with S-04 override.
- FAILURE CONDITIONS: a new class-ordering constant; touching `governor.py`.
- ROLLBACK: revert PR.
- ESCALATE WHEN: `agents.py` exposes no usable ordering (it is protected; do not edit it — escalate).
- EXPECTED OUTPUT: PR `S-04: capacity gate can only lower model class`.

## S-05 — macOS service definitions (launchd) mirroring systemd

- PRIORITY: P1 (owner: Mac readiness is active)
- OBJECTIVE: a Mac can run the same unattended loop as Mark-2.
- WHY: `systemd/` has 9 units; the only darwin-aware line in the repo is `learnrepo.py:555`.
- VERIFIED START STATE: `ls systemd/` shows the 9 units; `deploy/launchd/` does not exist.
- ALLOWED FILES: `deploy/launchd/*.plist` (new; override granted), `scripts/install_services.sh` (add a darwin branch; keep the linux branch byte-identical), `tests/test_launchd_units.py` (new), `systemd/README.md` is FORBIDDEN (protected, no override) — put Mac docs in `deploy/launchd/README.md`.
- EXACT ACTION: for each `aion-*.service`/`.timer` pair create `com.lucyos.<name>.plist` with `ProgramArguments` = the unit's `ExecStart` split into argv, `StartInterval` = the timer's `OnUnitActiveSec` in seconds, `WorkingDirectory`, `StandardOutPath`/`StandardErrorPath` under `$AION_HOME/logs/`, `RunAtLoad` true. Skip `mark2-*` units (host-specific; note this in the README). Test: every plist parses with `plistlib`, every `ProgramArguments[0]` exists relative to repo or is `python3`, every systemd `aion-*` unit has a plist counterpart.
- DEPENDENCIES: none
- MODEL CLASS: B
- TOKEN/COST BUDGET: ≤ 40k tokens
- TESTS: new file + full suite
- ACCEPTANCE: tests pass on Linux (plistlib is stdlib); macOS CI job runs them.
- FAILURE CONDITIONS: editing any systemd unit; hardcoding a user home path.
- ROLLBACK: delete `deploy/launchd/`.
- ESCALATE WHEN: a unit uses a systemd feature with no launchd analogue (document it, do not fake it).
- EXPECTED OUTPUT: PR `S-05: launchd units for the aion loop`.

## S-07 — `aion drive-check`: read/write capability probe for the Drive bridge

- PRIORITY: P2 (turns the Mark-2 "uploads broken" symptom into a diagnosable health line)
- OBJECTIVE: a deterministic command reporting whether the configured rclone remote can list, read, and write a probe file — without printing remote names, paths, or rclone stderr.
- VERIFIED START STATE: `bridges/drive_bridge.py` shells out to `rclone` (line 146-166); no write probe exists.
- ALLOWED FILES: `bridges/drive_bridge.py`, `aion_core/cli.py`, `aion_core/health.py` (add a non-required check `drive_bridge` that is `ok=True, required=False` when rclone is absent), `tests/test_drive_check.py` (new, mock subprocess).
- FORBIDDEN: `aion_core/security.py`; any change to what the bridge redacts.
- EXACT ACTION: add `capability()` to the bridge returning `{"list": bool, "read": bool, "write": bool, "detail": str}` using `rclone lsd`, `rclone cat` of a known probe, and `rclone rcat` of a 1-byte `.lucyos-write-probe` then delete; every subprocess result passes through `security.redact`. CLI `drive-check` prints it. Health check reuses it (deep=True only).
- DEPENDENCIES: none
- MODEL CLASS: B
- TOKEN/COST BUDGET: ≤ 40k
- TESTS: mocked subprocess for all three outcomes; full suite
- ACCEPTANCE: tests pass; `./aion drive-check` on a machine without rclone prints `rclone not installed` and exits 0.
- FAILURE CONDITIONS: printing raw rclone output; leaving the probe file behind on success.
- ROLLBACK: revert.
- ESCALATE WHEN: the write probe needs a remote-side setting change (owner action).
- EXPECTED OUTPUT: PR `S-07: drive-check read/write probe`.

## S-08 — Secret-scanner same-name kwarg exemption

- PRIORITY: P2
- OBJECTIVE: `token_budget=token_budget` (identifier equal to the assigned name) is no longer reported by `assigned_secret`.
- WHY: it fired twice in one day; friction pushes people toward `.secretscanignore`, which narrows real scanning.
- VERIFIED START STATE: `./aion scan` on a file containing `token_budget=token_budget,` reports `assigned_secret`.
- ALLOWED FILES: `aion_core/security.py` (override granted; only `_is_placeholder` / the `assigned_secret` handling), `tests/test_security.py`.
- FORBIDDEN: widening `_IDENTIFIER` to arbitrary snake_case (a lowercase secret with an underscore must still be caught); touching `.secretscanignore`.
- EXACT ACTION: in `scan_text`, for `assigned_secret` matches, treat the value as a placeholder when `value.strip(",;\"')") == match.group(1)` (the assigned name itself). Tests: `token_budget=token_budget` clean; `password=password` clean; an assignment whose value is a *different* credential-shaped word (reuse an existing fixture from `tests/test_security.py`, do not add a new literal) is still reported.
- DEPENDENCIES: none
- MODEL CLASS: B
- TOKEN/COST BUDGET: ≤ 15k
- ACCEPTANCE: the three tests; full suite; scan clean.
- FAILURE CONDITIONS: any currently-detected fixture in `tests/test_security.py` stops being detected.
- ROLLBACK: revert.
- ESCALATE WHEN: the exemption needs the regex changed.
- EXPECTED OUTPUT: PR `S-08: exempt same-name kwarg from assigned_secret`.

## S-09 — `aion openclaw-check`: loopback gateway reachability (optional, P2)

- OBJECTIVE: a deterministic, no-persistence probe reporting whether an OpenClaw gateway answers on loopback, so "DEGRADED: no persistent gateway" becomes a health line instead of tribal knowledge.
- ALLOWED FILES: `bridges/openclaw_check.py` (new), `aion_core/cli.py`, `aion_core/health.py` (non-required, deep only), `tests/test_openclaw_check.py`.
- FORBIDDEN: starting, installing, or configuring a gateway; any network target other than `127.0.0.1`/`localhost`; any credential.
- EXACT ACTION: HTTP GET to the configured loopback port (from `db.get_meta("openclaw_port", "")`, empty = "not configured"), 2 s timeout, report reachable/unreachable/not-configured.
- MODEL CLASS: A or B; BUDGET ≤ 15k; ROLLBACK revert; ESCALATE if the gateway needs auth to answer at all.

---

## Fable-owned follow-ups (not for Sonnet)

- FABLE-01 — After S-02..S-04 are merged: review the cumulative diff, `python3 scripts/verify_authority.py freeze --sha PENDING`, commit, then set `fable_freeze_sha` to that commit and name the Mark-2 deployment candidate SHA in `.lucy/deployment/MARK2_DEPLOYMENT_CONTRACT.md`.
- FABLE-02 — Once `macos-readiness` has one green run, remove `continue-on-error` and add it to required checks (constitutional path; owner merges).

## Owner-only (see execution package §15)

- OWNER-01 — Branch protection on `main` and on `integration/consolidation-20260916`: require PR, required checks `code-and-test`, `clean-bootstrap-health`, `upgrade-from-main-schema`, `authority-gate`; no direct pushes; admins may bypass (that is how Fable/owner changes land).
- OWNER-02 — Repository visibility → PRIVATE.
- OWNER-03 — Delete: `claude/aion-whatsapp-control-1seild`, `arch/lucyos-interface-m-a`, `candidate/mark2-loop-v1.2-20260908`, `feature/lucyos-aion-handoff`, and Q000–Q005 + `feature/learnrepo-queue-health` once the integration branch is protected. Tag `backup/pre-mark2-loop-v1.2-20260908` as `archive/pre-mark2-loop-v1.2` then delete the branch.
- OWNER-04 — rclone remote write scope on Mark-2 (S-07 will tell you exactly which capability is missing).
