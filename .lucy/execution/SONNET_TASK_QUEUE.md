# SONNET_TASK_QUEUE — LucyOS consolidation cycle 2026-09-16

Frozen by Fable (overnight pass). Canonical queue — there is no other.
Executors: Sonnet (class B) unless stated. Base branch for every task:
`integration/consolidation-20260916`. Branch naming is mandatory:
`task/<TASK_ID>-<slug>`. One task = one branch = one PR into the integration
branch. **Never merge.** Loop procedure lives in
`.lucy/handoffs/2026-09-16/06_SONNET_AUTONOMOUS_NIGHT_LOOP_PROMPT.txt`.

Governing contracts: `.lucy/authority/HIGH_MODEL_BASELINE.json`,
`PROTECTED_PATHS.md`, `LUCYOS_FABLE_ARCHITECT_EXECUTION_PACKAGE.md`, and
`LUCYOS_PLATFORM_AND_DATA_CONTRACTS.md` (C1–C10, new tonight).

**Standard gates for every task**, before opening the PR:

```
python3 -m unittest discover -s tests -t . -q
./aion scan .
python3 scripts/check_portability.py
python3 scripts/verify_authority.py strict  --base origin/integration/consolidation-20260916 --branch "$(git branch --show-current)"
python3 scripts/verify_authority.py anti-dup --base origin/integration/consolidation-20260916
```

Commit first line `<TASK_ID>: <what changed>`, plus a `Task-ID: <TASK_ID>` trailer.

---

## Classification (master-prompt requirement)

| Class | Items |
|---|---|
| **MUST BE FABLE/HIGH MODEL** | FABLE-01 re-freeze after merges · FABLE-02 promote `macos-readiness` to required · FABLE-03 name DC-1 deploy SHA · any change to `.lucy/authority/**`, the CI workflow, or `verify_authority.py` |
| **READY FOR SONNET NOW** | S-01, S-02, S-05, S-07, S-08, S-09, S-10, S-13, S-14, S-15, S-17, S-18, S-19, S-20, S-21, S-22, S-23, S-24, S-26, S-27, S-28, S-29 |
| **READY AFTER AN IN-NIGHT DEPENDENCY** | S-11, S-12 (need S-10 merged) · S-25 (needs S-05 merged) — if unmerged → `BLOCKED_DEPENDENCY`, take another task |
| **READY FOR LOCAL/DETERMINISTIC** | S-20, S-27, S-28 · mechanical parts of S-14 |
| **WAITING FOR OWNER** | S-03, S-04 (need S-02 merged) · OWNER-01..05 |
| **WAITING FOR FUTURE HARDWARE** | Mac-mini live validation of C1 · local Linux PC tests (~2 days) · Mark-2 deploy (DC-1) |
| **DEFERRED** | UI/UX (explicitly out of scope) · heavy Lucy Claw fork · telephony provisioning · SEVAACONNECT salvage · vector/embedding backend (needs evidence FTS is insufficient) |

**Overnight ordering.** Take READY tasks in this order, skipping any that is
blocked: **S-21, S-19, S-10, S-01, S-13, S-14, S-08, S-22, S-07, S-18, S-15,
S-23, S-17, S-05, S-09, S-24, S-26, S-27, S-20, S-28, S-29, S-02.** S-21 is first: the repository is public and a read-only history secret-scan is
cheap, and if it finds something the owner needs to know tonight, not tomorrow.
S-19 is next because it is the only thing standing between `macos-readiness`
and its first green run, which C1 needs; then S-10, which unblocks S-11/S-12.
S-02 is last among READY because it is a large salvage merge best reviewed with
fresh eyes. S-21…S-29 were swept from older repo queues — see
"Appended: survivors of the older repo queues".

---

## S-01 — Skill-registry policy-class normalization + upgrade regression test

- STATUS: READY · PRIORITY P0 · MODEL B · BUDGET ≤ 40k
- OBJECTIVE: legacy lowercase policy classes heal on `ensure_defaults()`; a regression test proves an upgraded database validates clean.
- WHY: `validate_registry()` (`aion_core/skills.py:203-210`) is case-sensitive; `register()` uppercases on write but the compatibility migration (`skills.py:163-164`) only maps word labels. Pre-Q005 rows with `f0`/`e1`/`r1`/`internal`/`p1` stay invalid forever. Live Mark-2 registry is DEGRADED by exactly this. The Drive patch `LUCYOS_STEP1_F0_MIGRATION_FIX.patch` fixes only `f0` — fix the **class** of bug, not the one value.
- VERIFIED START STATE: injecting `cost_class='e1'`, `risk_class='r1'`, `data_class='internal'` via SQL then calling `skills.ensure_defaults()` leaves `validate_registry()` returning 3 errors.
- ALLOWED: `aion_core/skills.py`, `tests/test_skills.py`, `tests/test_migrations.py` (new)
- FORBIDDEN: `aion_core/db.py` (the fix is in `ensure_defaults`, not the schema); changing `COST_CLASSES` or any enum; loosening `validate_registry()`
- ACTION:
  1. In `ensure_defaults()`, after the existing word-label UPDATEs (they must stay first so `local`→`F0` still works), add generic normalization for all four columns: `UPDATE skills SET cost_class=upper(cost_class) WHERE cost_class <> upper(cost_class)`, likewise `risk_class`, `data_class`, `priority`.
  2. New `tests/test_migrations.py`, class `TestUpgradeFromOldState(AionTest)`: (a) lowercase `f0` heals; (b) all four columns lowercase across different skills → `validate_registry() == []`; (c) idempotency — `ensure_defaults()` twice yields identical rows.
  3. Module docstring states the owner rule: every schema/enum/policy migration ships an upgrade-from-old-state test here.
- ACCEPTANCE: three new tests pass; full suite passes; no other file changed.
- ESCALATE: a case needs a schema change; any existing test breaks.

## S-02 — Salvage `claude/lucyos-architecture-audit-4o4q83`

- STATUS: READY · PRIORITY P1 · MODEL B · BUDGET ≤ 30k
- OBJECTIVE: bring that branch's code onto integration; archive its planning docs so one planning surface remains.
- WHY: carries the argv-based execution boundary (a security hardening). `git merge-tree` proves the merge is conflict-free. Its `docs/architect/*` duplicates `.lucy/`.
- VERIFIED START STATE: `git merge-tree --write-tree origin/integration/consolidation-20260916 origin/claude/lucyos-architecture-audit-4o4q83` prints a tree id with **no** `CONFLICT` line. If it conflicts, integration has moved → `BLOCKED_START_STATE_DRIFT`.
- ALLOWED: whatever the merge brings, plus `.lucy/archive/docs-architect-20260916/**` (new). Override granted: `aion_core/worker.py`.
- FORBIDDEN: editing merged code beyond the merge result; leaving `docs/architect/` at its original path.
- ACTION: `git merge --no-ff origin/claude/lucyos-architecture-audit-4o4q83`; then `git mv docs/architect .lucy/archive/docs-architect-20260916`; add a 3-line `.lucy/archive/README.md` (archived, superseded by `.lucy/`, do not resume from here).
- ACCEPTANCE: suite passes (count rises — the branch adds tests); portability guard green; anti-dup green; `docs/architect/` absent; strict gate passes with the S-02 override.
- ESCALATE: any conflict marker; anti-dup flags anything.

## S-03 — Salvage `feature/resource-governor` as `research_registry`

- STATUS: **BLOCKED_DEPENDENCY** until S-02 is merged into integration by the owner. Do not stack locally.
- PRIORITY P1 · MODEL B · BUDGET ≤ 80k
- OBJECTIVE: land the capacity governor flag-gated OFF, without the module-name collision.
- VERIFIED START STATE: `git merge-tree --write-tree` against integration reports CONFLICT in `cli.py`, `db.py`, `health.py`, `learnrepo.py` (add/add).
- ALLOWED: what the cherry-pick brings; `aion_core/research_registry.py` (new); `aion_core/resource_governor/**`; `cli.py`; `health.py`; `bootstrap.py`; `tests/test_resource_governor_*.py`; `tests/test_research_registry.py`. Overrides: `db.py`, `worker.py`, `resume.py`, `router.py`, `.secretscanignore`.
- FORBIDDEN: changing any default flag value (admission stays OFF); changing Q006 `learnrepo.py` semantics; tables outside `db.py`.
- ACTION: `git cherry-pick -x 1d6aa7ef67f77a381a3591933f356113e029753e`; resolve `cli.py`/`db.py`/`health.py` additively keeping both sides (Q006 first; new tables after the `learnrepo_*` ones); for the `learnrepo.py` add/add keep **OURS** (Q006, 669 lines) and write **THEIRS** (78 lines) to `aion_core/research_registry.py`, changing only the docstring's first line; repoint every registry import (`resource_governor/__init__.py`, `capability_gate.py`, `providers/__init__.py` docstring, `bootstrap.py:144`, and the `resource-governor learnrepo` CLI sub-op → rename to `research`).
- ACCEPTANCE: `python3 -c "import aion_core.research_registry, aion_core.learnrepo"` works; admission flag still defaults False (assert it in a test); all gates green.

## S-04 — Governor precedence: capacity gate may only lower

- STATUS: **BLOCKED_DEPENDENCY** on S-03 · PRIORITY P1 · MODEL B · BUDGET ≤ 30k
- OBJECTIVE: machine-check contract D3 — the capacity gate may lower a task's model class or skip it, never raise one the spend governor already lowered.
- ALLOWED: `aion_core/worker.py` (override, only inside `_resource_governor_gate`), `aion_core/resource_governor/admission.py`, `tests/test_governor_precedence.py` (new)
- FORBIDDEN: `aion_core/governor.py`; any new class-ordering constant — reuse `agents.ORDER` (`["DET","A","B","C","D"]`).
- ACTION: clamp in `_resource_governor_gate`: if `class_override` ranks higher than `cls` on `agents.ORDER`, ignore it and record note `"capacity gate attempted upgrade; refused"`.
- ACCEPTANCE: with the flag forced on in-test, proposing `C` for a `B` task yields `B`; proposing `A` yields `A`; a `skip` still skips.

## S-05 — macOS launchd units mirroring systemd

- STATUS: READY · PRIORITY P1 (owner: Mac readiness is active) · MODEL B · BUDGET ≤ 40k
- OBJECTIVE: a Mac can run the same unattended loop as Mark-2.
- ALLOWED: `deploy/launchd/*.plist` (new; override granted), `deploy/launchd/README.md` (new), `scripts/install_services.sh` (add a darwin branch; leave the linux branch byte-identical), `tests/test_launchd_units.py` (new)
- FORBIDDEN: `systemd/**` (protected, no override — put Mac docs in `deploy/launchd/README.md`); hard-coding any user home path.
- ACTION: create exactly **four** plists. The units are not uniform, so translate per this table — do not assume a `.service`/`.timer` pair everywhere:

  | systemd source | plist | launchd scheduling key |
  |---|---|---|
  | `aion-work.service` + `aion-work.timer` (`OnBootSec=2min`) | `com.lucyos.aion-work.plist` | `RunAtLoad true`; no calendar key. `OnBootSec` has no exact launchd analogue — document the difference in the README rather than inventing one. |
  | `aion-maintenance.service` + `aion-maintenance.timer` (`OnCalendar=*-*-* 03:15:00`) | `com.lucyos.aion-maintenance.plist` | `StartCalendarInterval = {Hour: 3, Minute: 15}` |
  | `aion-bridge.service` (long-running, `Restart=always`) | `com.lucyos.aion-bridge.plist` | `RunAtLoad true` + `KeepAlive true` |
  | `aion-interface.service` (long-running, `Restart=always`) | `com.lucyos.aion-interface.plist` | `RunAtLoad true` + `KeepAlive true` |

  Each plist: `ProgramArguments` = that unit's `ExecStart` split into argv, **keeping the existing `@REPO@` / `@AION_HOME@` placeholder convention** (`install_services.sh` substitutes them — do not bake absolute paths); `WorkingDirectory`; `StandardOutPath`/`StandardErrorPath` under `@AION_HOME@/logs/`. Skip `mark2-*` units — host-specific; say so in the README.
- ACCEPTANCE: every plist parses with `plistlib` (stdlib, so the test runs on Linux too); every `ProgramArguments[0]` is non-empty and placeholder-substitutable; all four `aion-*` units have a counterpart and no plist references a path outside the placeholders — asserted, not assumed.
- ESCALATE: a unit uses a systemd feature with no launchd analogue — document it, do not fake it.

## S-07 — `aion drive-check`: read/write capability probe

- STATUS: READY · PRIORITY P2 · MODEL B · BUDGET ≤ 40k
- OBJECTIVE: turn "Mark-2 Drive uploads are broken" into a diagnosable health line, without exposing remote names, paths or rclone stderr.
- WHY: C2 — Drive is transport, and we need to know *which* capability is missing (OWNER-04 acts on the answer). Fixing OAuth is explicitly **not** tonight's job.
- ALLOWED: `bridges/drive_bridge.py`, `aion_core/cli.py`, `aion_core/health.py`, `tests/test_drive_check.py` (new)
- FORBIDDEN: `aion_core/security.py`; changing what the bridge redacts; making any Drive write a precondition for anything.
- ACTION: add `capability()` returning `{"list": bool, "read": bool, "write": bool, "detail": str}` using `rclone lsd`, a read of a known probe, and `rcat` of a 1-byte `.lucyos-write-probe` which is then deleted. Every subprocess result passes through `security.redact`. CLI `drive-check` prints it. Health adds a **non-required** `drive_bridge` check (`required=False`, deep only) that is `ok=True` when rclone is absent.
- ACCEPTANCE: mocked subprocess covers all three outcomes; `./aion drive-check` on a machine without rclone prints "rclone not installed" and exits 0; probe file never survives a success.

## S-08 — Secret-scanner same-name kwarg exemption

- STATUS: READY · PRIORITY P2 · MODEL B · BUDGET ≤ 15k
- OBJECTIVE: `token_budget=token_budget` stops being reported as `assigned_secret`.
- WHY: it fired twice in one day; friction pushes people toward `.secretscanignore`, and every entry there stops a real file being scanned.
- ALLOWED: `aion_core/security.py` (override granted; only `_is_placeholder` / the `assigned_secret` handling), `tests/test_security.py`
- FORBIDDEN: widening `_IDENTIFIER` to arbitrary snake_case (a lowercase secret with an underscore must still be caught); touching `.secretscanignore`.
- ACTION: in `scan_text`, for `assigned_secret` matches treat the value as a placeholder when `value.strip(",;\"')") == match.group(1)` — the assigned name repeated.
- ACCEPTANCE: `token_budget=token_budget` clean; `password=password` clean; every existing detection fixture in `tests/test_security.py` still detected (that is the real test).

## S-09 — `aion openclaw-check`: loopback reachability probe

- STATUS: READY · PRIORITY P2 · MODEL A or B · BUDGET ≤ 15k
- OBJECTIVE: make "OpenClaw has no persistent gateway" a health line instead of tribal knowledge.
- ALLOWED: `bridges/openclaw_check.py` (new), `aion_core/cli.py`, `aion_core/health.py`, `tests/test_openclaw_check.py` (new)
- FORBIDDEN: starting/installing/configuring a gateway; any network target other than `127.0.0.1`/`localhost`; any credential; anything that makes OpenClaw canonical (C4).
- ACTION: HTTP GET the configured loopback port from `db.get_meta("openclaw_port", "")` (empty = "not configured"), 2 s timeout; report reachable / unreachable / not-configured.
- ACCEPTANCE: all three states tested with a stub; non-required health check; no outbound non-loopback request.

## S-10 — `aion_core/host/`: the platform adapter layer

- STATUS: READY · PRIORITY P1 · MODEL B · BUDGET ≤ 50k · **unblocks S-11, S-12**
- OBJECTIVE: create the adapter package frozen in contract C1. Pure addition — migrate nothing yet.
- ALLOWED: `aion_core/host/__init__.py`, `base.py`, `linux.py`, `macos.py` (all new), `tests/test_host_adapter.py` (new)
- FORBIDDEN: editing any existing module (S-11/S-12 do the migrations); importing `linux`/`macos` from anywhere but `host/__init__.py`; putting business logic in an adapter.
- ACTION: implement exactly the C1 table — `name()`, `scheduler_kind()`, `service_unit_dir()`, `service_active(name)`, `service_install_hint(name)`, `probe()`. `current()` selects by platform and returns a conservative fallback adapter on an unknown platform (`"native-timer"`, `service_active()` → `None`) that never raises on import.
- ACCEPTANCE: `service_active()` returns **`None`**, never `False`, when it cannot determine — asserted directly; tests for both adapters run on any platform (inject the platform, never require it); `aion_core/host/**` is the only portability-guard-exempt path and the guard stays green.
- ESCALATE: a method in the C1 table cannot be implemented portably — report it, do not invent a seventh method.

## S-11 — Migrate `learnrepo.scheduler_kind` behind the host adapter

- STATUS: **BLOCKED_DEPENDENCY** until S-10 is on integration · PRIORITY P1 · MODEL B · BUDGET ≤ 20k
- ALLOWED: `aion_core/learnrepo.py`, `scripts/check_portability.py` (override granted — **only** to delete its own two `KNOWN_EXCEPTIONS` entries), `tests/test_learnrepo.py`
- FORBIDDEN: any other change to the guard (thresholds, rules, scope); leaving a stale exception.
- ACTION: replace the inline `platform.system()` branch at `learnrepo.py:554-555` with `host.current().scheduler_kind()`; delete `aion_core/learnrepo.py::init_system` and `::os_branch` from `KNOWN_EXCEPTIONS`.
- ACCEPTANCE: guard green with **2 fewer** exceptions and 0 stale; existing learnrepo tests unchanged and passing; `platform.node()` usage at line 517 left alone (identity, not an OS branch).

## S-12 — Migrate `drive_bridge` readiness check behind the host adapter

- STATUS: **BLOCKED_DEPENDENCY** until S-10 is on integration · PRIORITY P1 · MODEL B · BUDGET ≤ 20k
- OBJECTIVE: stop reporting "timer not active" on macOS when the launchd equivalent **is** running.
- WHY: `ready_handoff()` (`bridges/drive_bridge.py:424`) shells to `systemctl`; on macOS that raises, is swallowed, and the readiness document then states a falsehood. C1 requires "cannot determine" to be rendered as unknown.
- ALLOWED: `bridges/drive_bridge.py`, `scripts/check_portability.py` (override — **only** to delete its own entry), `tests/test_drive_bridge.py`
- FORBIDDEN: any other change to the guard (rules, scope, thresholds, another task's entry); adding a platform branch in the bridge (C1 — ask the adapter); changing anything else `ready_handoff()` writes; making the readiness document claim a state it did not verify.
- ACTION: call `host.current().service_active("mark2-drive.timer")`; render `True`→"active", `False`→"not active", `None`→**"unknown (cannot determine on this host)"**.
- ACCEPTANCE: a test asserts all three renderings, including that `None` never prints "not active"; guard green with 1 fewer exception.

## S-13 — `sync_outbox`: the local-first PENDING_SYNC ledger

- STATUS: READY · PRIORITY P1 · MODEL B · BUDGET ≤ 60k
- OBJECTIVE: implement contract C2's ledger so outbound Drive work is durable and Drive is never a precondition.
- ALLOWED: `aion_core/sync_outbox.py` (new), `aion_core/db.py` (override — additive table only), `aion_core/cli.py`, `tests/test_sync_outbox.py` (new)
- FORBIDDEN: a second database or queue (anti-dup will fail you); any network call; making Drive availability a precondition; absolute paths in `local_path`.
- ACTION: create the `sync_outbox` table exactly as specified in C2 §"Frozen model" via the existing additive-migration pattern; implement `queue(kind, local_path, project="", remote_target="")` → sync_id, `claim(sync_id, by)`, `mark_synced(sync_id)`, `mark_conflict(sync_id, detail)`, `pending()`, `backlog()`. `content_hash` = `util.sha256_file`.
- ACCEPTANCE: queuing identical content twice yields **one** row (idempotency proven, not asserted in prose); a full local cycle completes with no network and no rclone present; `pending()` survives a process restart; status transitions are legal-only (illegal transition raises).
- ESCALATE: conflict resolution appears to need a policy choice beyond local-wins-with-evidence.

## S-14 — Data intake provenance contract

- STATUS: READY · PRIORITY P1 · MODEL B (mechanical parts suit a local model) · BUDGET ≤ 60k
- OBJECTIVE: implement contract C3's metadata envelope so cross-project learning stays reversible.
- ALLOWED: `aion_core/intake.py` (new), `aion_core/db.py` (override — additive), `tests/test_intake.py` (new)
- FORBIDDEN: any embedding/vector backend (C3 forbids it without evidence); mutating a raw record; defaulting `training_eligible` to True.
- ACTION: implement `record(source, kind, payload_path, *, project="", confidentiality="INTERNAL", ...)` writing the full C3 field set. Reuse `skills.DATA_CLASSES` for `confidentiality` — do **not** define a parallel enum. Tiers (`raw`/`normalized`/`derived`/`curated`/`index`/`export`) are a column, not separate tables.
- ACCEPTANCE: a record missing any required provenance field is **rejected** (test proves it); `training_eligible` defaults False; a raw record cannot be mutated — a correction creates a new record referencing the original; retrieval uses filters/FTS only.

## S-15 — Prove LucyOS runs with no OpenClaw present

- STATUS: READY · PRIORITY P1 · MODEL B · BUDGET ≤ 25k
- OBJECTIVE: turn contract C4's replaceability claim into a test.
- ALLOWED: `tests/test_openclaw_independence.py` (new)
- FORBIDDEN: touching runtime code — if the test fails, that is a finding to escalate, not a licence to change architecture tonight.
- ACTION: with no OpenClaw process, no gateway port configured and no related env var, assert a clean `AION_HOME` can `init`, `seed`, create and transition a task, create and decide an approval, take and verify a backup, and `boot`.
- ACCEPTANCE: passes with zero OpenClaw dependency; if it fails, open the PR with the failing test and mark `BLOCKED_HIGH_MODEL_DECISION` — a red test here is genuinely valuable information.

## S-16 — Temporary-worker scope narrowing and TTL (guard rails only)

- STATUS: READY · PRIORITY P2 · MODEL B · BUDGET ≤ 45k
- OBJECTIVE: give contract C6 its enforcement primitives. **Guard rails only — this task does not spawn anything.**
- WHY: C6 allows Lucy to create bounded temporary workers later. The limits must exist and be tested *before* anything can create one, not after.
- ALLOWED: `aion_core/agents.py` is **FORBIDDEN** (protected, no override) — instead add `aion_core/tempworker.py` (new), `aion_core/db.py` (override — additive columns/table only), `tests/test_tempworker.py` (new)
- FORBIDDEN: creating/spawning a worker; any new agent framework or scheduler (anti-dup will fail you); widening any existing scope; granting a capability not already held by the parent.
- ACTION: implement `derive(parent_scope, requested_scope, ttl_seconds)` returning a scope that is the **intersection** of parent and requested — never a superset — plus `expires_at`; `is_expired(worker)`; `assert_can_claim(worker)` which refuses an expired or out-of-scope claim. Reuse the existing `agents`/`tasks` tables; store TTL as additive columns.
- ACCEPTANCE: a child requesting a capability the parent lacks gets a **narrower** scope, never the requested one (asserted); scope narrowing is transitive across three generations; an expired worker cannot claim a task; TTL is enforced on read, not by a background sweeper (no second scheduler).
- ESCALATE: enforcing C6 appears to require editing `agents.py` — stop and report; do not use the override you were not given.

## S-17 — Deployment-guardian skeleton (disabled)

- STATUS: READY · PRIORITY P2 · MODEL B · BUDGET ≤ 50k
- OBJECTIVE: encode contract C5's pipeline as a deterministic state machine that **cannot deploy**.
- ALLOWED: `aion_core/guardian.py` (new), `tests/test_guardian.py` (new)
- FORBIDDEN: any actual deploy, service restart, or network call; enabling autonomy; a second scheduler; treating an exit code as evidence.
- ACTION: implement the ordered stages SNAPSHOT → ISOLATE → IMPLEMENT → TEST → STATIC/SECURITY → INDEPENDENT VERIFY → STAGE → HEALTH CHECK → LIMITED DEPLOY → MONITOR → AUTO-ROLLBACK → EVIDENCE. Each stage records evidence; `advance()` refuses to skip a stage or to advance without evidence. A hard `ENABLED = False` module constant gates LIMITED DEPLOY entirely.
- ACCEPTANCE: refuses to advance without evidence; refuses to skip; an injected failure at each stage triggers rollback; LIMITED DEPLOY raises while `ENABLED` is False — all proven by tests.

## S-18 — Recovery evidence: corrupted-state and failure injection

- STATUS: READY · PRIORITY P0 (recoverability is a readiness gate) · MODEL B · BUDGET ≤ 40k
- OBJECTIVE: prove recovery against real damage, not mocks.
- ALLOWED: `tests/test_recovery_injection.py` (new)
- FORBIDDEN: modifying backup/restore code to make a test pass — a failure here is a real finding; weakening any assertion.
- ACTION: on a throwaway `AION_HOME`: take a backup, then (a) truncate the SQLite file, (b) corrupt its header bytes, (c) delete it outright, (d) kill mid-write by removing the `-wal`. For each, assert the damage is *detected* (`integrity_check` or health fails — never silently "ok"), restore from backup succeeds, and post-restore `validate_registry()`/task counts match pre-damage.
- ACCEPTANCE: four scenarios, each proving detect → restore → verify. If any damage is **not** detected, that is a genuine P0 finding: open the PR with the failing test and escalate.

## S-19 — Fix macOS symlinked-tmp rejection in `read_safe`

- STATUS: READY · PRIORITY P1 · MODEL B · BUDGET ≤ 40k · **take this first**
- OBJECTIVE: `macos-readiness` reaches its first green run without weakening the bridge's security property.
- WHY: `bridges/drive_bridge.py:129` rejects a path if **any** ancestor is a symlink. On macOS `$RUNNER_TEMP`/`$TMPDIR` resolve under `/var/folders/...` and `/var` is itself a symlink to `/private/var`, so all four drive-bridge staging tests fail with `rejected_source`. The check's real intent is **containment** (no reading outside the intended tree), which the ancestor-symlink rule only approximates — and approximates wrongly on macOS.
- FROZEN DESIGN (do not redesign): keep rejecting a symlinked **leaf** (the `O_NOFOLLOW` open and the leaf `is_symlink()` check stay). Replace the *ancestor* symlink rule with a containment assertion: resolve the path with `Path.resolve()` and require the result to be inside the resolved allowed root (the bridge's own tree / `AION_HOME`). Keep the `BLOCK` name pattern check and the `st_nlink != 1` hardlink rejection exactly as they are.
- ALLOWED: `bridges/drive_bridge.py`, `tests/test_drive_bridge.py`
- FORBIDDEN: relaxing the hardlink check; relaxing `BLOCK`; allowing a resolved path outside the allowed root; adding a platform branch (C1 — the fix must be one portable code path); `continue-on-error` anywhere.
- ACCEPTANCE: **every existing rejection test in `tests/test_drive_bridge.py` still rejects** (this is the real acceptance criterion); plus a new test proving a file under a symlinked-ancestor tmp dir *inside* the allowed root is accepted, and one proving a symlink escaping the root is still refused; suite green on Linux; `macos-readiness` green in CI on the PR.
- ESCALATE: containment cannot be expressed without a platform branch, or any existing rejection test would have to change.

## S-20 — Regenerate `PROTECTED_PATHS.md` human table from the baseline

- STATUS: READY · PRIORITY P2 · MODEL A (local/deterministic suits this) · BUDGET ≤ 15k
- OBJECTIVE: remove drift risk between the machine baseline and its human explanation.
- ALLOWED: `scripts/render_protected_paths.py` (new), `tests/test_render_protected_paths.py` (new)
- FORBIDDEN: `.lucy/authority/**` (constitutional — the script *renders* to stdout and the test compares; **Fable** applies the result later). Do not write into the authority directory.
- ACTION: script reads `HIGH_MODEL_BASELINE.json` and prints the markdown table of protected/constitutional paths. Test asserts every `protected_paths` entry appears in the current `PROTECTED_PATHS.md`, failing loudly when the two drift.
- ACCEPTANCE: the drift test passes today and would fail if a path were added to the baseline alone.

---

# Appended: survivors of the older repo queues

Swept 2026-09-16 from every other task list in the repo and on its branches:
`docs/architect/05_LOW_MODEL_TASK_QUEUE.md` (LQ-01…LQ-20, on
`claude/lucyos-architecture-audit-4o4q83`), `deploy/queues/M-A_structured_api.md`,
`deploy/queues/M-A.4_assessment.md`, and the SEVAA queues on
`claude/fable-deploy-setup-mc5nr6`. Each item was **checked against the live
tree**, not taken on trust. Survivors below, in the order they should be done;
everything else is discarded with its reason in the next section.

These run **after** S-01…S-20, except **S-21, which should be pulled forward** —
the repository is public and a history secret-scan is cheap and read-only.

## S-21 — Read-only git-history secret scan (was LQ-04)

- STATUS: READY · PRIORITY P0 · MODEL B · BUDGET ≤ 30k
- WHY: the repo is **public** by current owner decision. `./aion scan .` only
  sees the working tree; a secret committed and later deleted still lives in
  history and is still public. Never verified.
- ALLOWED: `scripts/scan_history.py` (new), `tests/test_scan_history.py` (new)
- FORBIDDEN: rewriting history; deleting/force-pushing anything; printing a
  matched secret value into logs or the report (report path + commit + rule only);
  committing any found secret as a test fixture.
- ACTION: walk `git rev-list --all` blobs, run them through the existing
  `aion_core.security` patterns, report `commit / path / rule` with values
  redacted. Read-only — the script must not mutate the repo.
- ACCEPTANCE: clean run on the current history, or a redacted finding list;
  a synthetic planted secret in a temp repo is detected (proves it works);
  no secret value ever appears in output.
- ESCALATE: a real credential is found → **stop, report to the owner privately,
  do not commit the finding**. Rotation is owner-only.

## S-22 — Remove Desktop Commander from the repo (was LQ-11)

- STATUS: READY · PRIORITY P1 · MODEL B · BUDGET ≤ 15k
- WHY: `systemd/mark2-desktop-commander.service` is still present — a broad
  remote-control surface shipped in a public repo. Verified still there.
- ALLOWED: `systemd/mark2-desktop-commander.service` (deletion; override
  granted), `docs/` references, `tests/test_launchd_units.py` if S-05 landed
- FORBIDDEN: touching any other unit; deleting anything still referenced by a
  live install path without saying so in the PR.
- ACTION: remove the unit and its references; note in the PR what an operator
  who relied on it must do instead.
- ACCEPTANCE: no reference survives (`grep -ri "desktop.commander"` clean);
  suite green; if S-05 landed, its unit-parity test still passes.

## S-23 — `aion export` / `aion import` (was LQ-09)

- STATUS: READY · PRIORITY P1 · MODEL B · BUDGET ≤ 50k
- WHY: directly serves the coming **Mac migration** — today there is no
  supported way to move a shared brain between hosts. Verified absent.
- ALLOWED: `aion_core/portability.py` (new), `aion_core/cli.py`, `tests/test_portability_export.py` (new)
- FORBIDDEN: including `private_state/` or any secret in an export (**hard
  requirement**); absolute paths in the archive; a second backup system —
  reuse `aion_core/backup.py` primitives.
- ACTION: `export` writes a portable archive of canonical state with a manifest
  (schema version, content hashes, source host); `import` verifies the manifest
  and refuses a schema it does not understand rather than guessing.
- ACCEPTANCE: export → import into a fresh `AION_HOME` reproduces task and
  memory counts exactly; a tampered manifest hash is refused; a test asserts
  **no secret and no absolute path** is present in the archive; round-trip works
  with the source `AION_HOME` deleted between steps.

## S-24 — Encrypted backup artifact + documented off-host drill (was LQ-02)

- STATUS: READY · PRIORITY P1 · MODEL B · BUDGET ≤ 45k
- WHY: backups exist and restore-verify, but they are **local and unencrypted**.
  One lost machine loses everything. Verified: no restic, no encryption.
- ALLOWED: `aion_core/backup.py`, `docs/OPERATIONS.md`, `tests/test_backup_encryption.py` (new)
- FORBIDDEN: installing restic or any dependency (LucyOS is stdlib-only —
  document the off-host procedure instead of automating it tonight); storing or
  requesting a passphrase in git/logs/chat; **weakening the existing restore
  verification**; uploading anything anywhere.
- ACTION: add optional symmetric encryption of the backup artifact using a
  passphrase read from the existing secret store (absent → backup proceeds
  unencrypted and *says so* in its output, never silently). Document the
  off-host copy drill for an operator; automate nothing that needs credentials.
- ACCEPTANCE: encrypted backup round-trips through `backup.verify()`; wrong
  passphrase fails cleanly with a clear error, never a corrupt "success"; with
  no passphrase configured, existing behaviour is byte-identical (regression
  test); no secret in the artifact filename or logs.

## S-25 — Non-root service identity, cross-platform (was LQ-10)

- STATUS: **BLOCKED_DEPENDENCY** until S-05 lands (needs `deploy/launchd/`) · PRIORITY P1 · MODEL B · BUDGET ≤ 35k
- WHY: no unit sets `User=` — verified. Services would run as the invoking user,
  root in a typical install. Now also a C1 concern: the fix must be one portable
  approach, not a Linux-only one.
- ALLOWED: `systemd/*.service` (override granted), `deploy/launchd/*.plist`,
  `scripts/install_services.sh`, `docs/OPERATIONS.md`, `tests/test_service_identity.py` (new)
- FORBIDDEN: creating or modifying an OS account from any script (owner action —
  document it); a platform branch inside `aion_core/` (C1); hard-coded usernames.
- ACTION: add `User=`/`Group=` placeholders to systemd units and the launchd
  `UserName` equivalent, substituted by the installer like `@REPO@`/`@AION_HOME@`;
  document the owner step that creates the account.
- ACCEPTANCE: every long-running unit declares a non-root identity placeholder;
  a test asserts no unit runs as root by default; install script still idempotent.

## S-26 — Hash-chained audit export (was LQ-17)

- STATUS: READY · PRIORITY P2 · MODEL B · BUDGET ≤ 35k
- WHY: `events` is the audit trail but nothing makes tampering detectable.
- ALLOWED: `aion_core/reports.py`, `aion_core/cli.py`, `tests/test_audit_chain.py` (new)
- FORBIDDEN: altering the `events` schema or any existing row (append-only
  export, not a rewrite); a second log store.
- ACTION: export events with each record carrying the hash of the previous one;
  add verification that detects insertion, deletion or modification.
- ACCEPTANCE: an untouched export verifies; modifying, inserting or deleting any
  record fails verification — all three proven separately.

## S-27 — Routing telemetry report (was LQ-15)

- STATUS: READY · PRIORITY P2 · MODEL A or B · BUDGET ≤ 25k
- WHY: `model_usage` is populated but there is no report, so routing/spend
  decisions rest on impressions rather than data. Verified table exists.
- ALLOWED: `aion_core/reports.py`, `aion_core/cli.py`, `tests/test_routing_report.py` (new)
- FORBIDDEN: any model/API call to produce the report (deterministic SQL only);
  a new table.
- ACCEPTANCE: report over seeded rows matches hand-computed totals; empty data
  yields an honest "no usage recorded", never a fabricated zero-cost claim.

## S-28 — Sanitized runtime inventory script (was LQ-05)

- STATUS: READY · PRIORITY P2 · MODEL A or B · BUDGET ≤ 20k
- WHY: Mac + second Linux box are imminent; capturing what a host actually
  provides, with nothing sensitive in it, makes those migrations evidence-based.
- ALLOWED: `scripts/runtime_inventory.py` (new), `tests/test_runtime_inventory.py` (new)
- FORBIDDEN: emitting hostnames, usernames, absolute home paths, IPs, env values
  or secrets; any network call; a platform branch outside `aion_core/host` (call
  the adapter from S-10 where a platform fact is needed).
- ACCEPTANCE: output passes `security.redact` unchanged (i.e. contains nothing
  secret-shaped); a test asserts no username/home path leaks; runs on Linux and macOS.

## S-29 — Salvage `experiments.py` / `money_path.py` (was M-A.4)

- STATUS: READY · PRIORITY P2 · MODEL B · BUDGET ≤ 30k
- WHY: `deploy/queues/M-A.4_assessment.md` already proved these two modules
  apply cleanly in isolation (their *tests* were the conflict surface, not the
  logic). Verified: both files are still absent from the tree.
- ALLOWED: `aion_core/experiments.py`, `aion_core/money_path.py` (both new, via
  `git checkout origin/claude/fable-deploy-setup-mc5nr6 -- <path>`),
  `tests/test_experiments.py`, `tests/test_money_path.py`, `aion_core/cli.py`
- FORBIDDEN: cherry-picking the whole source commit `45403ba` (10 files conflict
  — the assessment documents exactly why); pulling in SEVAA/phone-interface code
  (owner deferred SEVAACONNECT); new tables outside `db.py`.
- ACTION: check out only the two modules, then port their tests to the current
  test base rather than importing the old fixtures wholesale.
- ACCEPTANCE: both modules import; their tests pass against the current tree;
  anti-dup green; nothing SEVAA-related enters the diff.
- ESCALATE: either module turns out to need a schema change — that is a Fable
  decision, not a salvage.

---

## Discarded from the older queues, with reasons

Recorded so nobody re-derives them later and thinks they were forgotten.

| Item | Disposition |
|---|---|
| LQ-01 argv execution boundary | **DONE** — implemented on `claude/lucyos-architecture-audit-4o4q83`; lands via S-02 |
| LQ-03 GitHub Actions CI | **DONE** — workflow exists and is green on both branches |
| LQ-19 curl/bash path constraints | **FOLDED** into LQ-01 by its own author |
| LQ-08 canonical authority policy doc + git guard | **SUPERSEDED** by `.lucy/authority/**` + `scripts/verify_authority.py` |
| LQ-14 capability manifest schema/validator/clamping | **SUPERSEDED** by Q002/Q005 (`skills/manifest.schema.json`, already in the Q006 lineage) |
| LQ-20 policy root + boot hash check + `aion policy accept` | **SUPERSEDED** by `verify_authority.py self` / `deploy` hash verification |
| LQ-13 documents/sources/claims/evidence + FTS5 · LQ-18 document intake skeleton | **FOLDED** into S-14 and contract C3, which cover provenance, tiering and FTS-before-vector. The claims/evidence *linkage* idea is preserved there via `entity_refs`. |
| LQ-06 approval object v2 | **NOT SONNET** — `approvals.py` is protected and this redesigns an authority object. Moved to **FABLE-04**. |
| LQ-07 agent registry cleanup | **DISCARDED** — stale; the registry was reshaped by Q001/Q005 and the original complaint no longer describes the code |
| LQ-12 inference-node qualification runbook | **WAITING FOR HARDWARE** — revisit when the Mac mini (24 GB) and the second Linux box exist |
| LQ-16 Telegram fallback adapter | **DEFERRED** — a new external service; owner said not tonight |
| `deploy/queues/M-A_structured_api.md` | **DONE** — `/api/v1/snapshot`, `/api/v1/money`, `/api/v1/projects` are live in `bridges/http_server.py` via `aion_core/api.py`. The file is a completed milestone record, not an open queue. |
| SEVAA queues (`PROJECTS/sevaa-sales-os/AION_TASK_QUEUE.md`, `AGENT_TASKS.json`, `deploy/fable/FABLE_TASK_QUEUE.md` on `claude/fable-deploy-setup-mc5nr6`) | **DEFERRED** — owner deferred SEVAACONNECT until consolidation is stable |
| `TOMORROW.md` | **NOT A SONNET QUEUE** — owner-facing install runbook. Left alone, but it predates this cycle and should be refreshed by the owner/Fable after the Mac migration. |

---

## Fable-owned (not for Sonnet)

- **FABLE-01** — after S-02/S-03/S-04 merge: review the cumulative diff, `python3 scripts/verify_authority.py freeze --sha PENDING`, commit, set `fable_freeze_sha` to that commit.
- **FABLE-02** — once `macos-readiness` has one green run (S-19 enables this), remove `continue-on-error` and add it to required checks.
- **FABLE-03** — name the DC-1 deployment SHA in `MARK2_DEPLOYMENT_CONTRACT.md` after FABLE-01.

## Owner-only

- **OWNER-01** — branch protection on `main` and `integration/consolidation-20260916`. Required checks, **exactly as GitHub renders them** (the matrix job expands per Python version — selecting a bare `code-and-test` will not match anything):
  - `code-and-test (py3.9)`
  - `code-and-test (py3.11)`
  - `code-and-test (py3.13)`
  - `clean-bootstrap-health`
  - `upgrade-from-main-schema`
  - `authority-gate`

  Leave `macos-readiness` and `authority-drift` **unrequired** for now (advisory/informational by design; FABLE-02 promotes the first once S-19 makes it green). Keep admin bypass enabled — it is the documented landing path for constitutional PRs.
- **OWNER-02** — **SUPERSEDED**: repo stays PUBLIC temporarily until the Mac migration completes. Do not change visibility. Compensating control: treat everything committed as public.
- **OWNER-03** — after protection: delete `claude/aion-whatsapp-control-1seild`, `arch/lucyos-interface-m-a`, `candidate/mark2-loop-v1.2-20260908`, `feature/lucyos-aion-handoff`, and Q000–Q005 + `feature/learnrepo-queue-health`; tag `backup/pre-mark2-loop-v1.2-20260908` as `archive/pre-mark2-loop-v1.2` then delete the branch.
- **OWNER-04** — rclone remote write scope on Mark-2 (S-07 reports exactly which capability is missing).
- **OWNER-05** — merge the night's task PRs into integration in queue order so the blocked chain (S-03, S-04, S-11, S-12) can proceed.

## Explicitly deferred

UI/UX · heavy Lucy Claw fork · telephony provisioning · SEVAACONNECT salvage
(`claude/fable-deploy-setup-mc5nr6`, 31 behind — selective salvage only, once
consolidation is stable) · any vector/embedding backend (C3: needs evidence
that filters + FTS are genuinely insufficient) · real-capital anything (C9).
