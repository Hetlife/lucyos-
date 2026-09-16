# LucyOS — Opus → Fable Architect Brief

Produced by: Opus, pre-architect auditor
Date: 2026-09-16
Planning branch: `planning/opus-fable-20260916`
Audited lineage: `feature/skill-system-q006-architecture-guard` @ `2b59aea7d785bbc42139dcb361834bb48ae158a3`
Scope: read-only audit + planning artifacts. No functional code was modified. No merge, no deploy.

**How to read this.** Every claim carries the command or file that produced it.
Where I could not verify something, it is marked UNKNOWN rather than guessed.
Claims inherited from `00_READ_ME_FIRST.md` were re-tested, not assumed — two
were confirmed, one was confirmed *and found to be broader than reported*.

---

## 1. Evidence-backed current-state matrix

Classification: ABSENT / DESIGNED / IMPLEMENTED / TESTED / CI_VERIFIED / DEPLOYED / LIVE_VERIFIED / DEGRADED / BROKEN / UNKNOWN.

**No capability anywhere in LucyOS can currently be classified CI_VERIFIED, because no CI exists on any branch (§6).** The ceiling for everything below is TESTED.

| Capability | State | Evidence |
|---|---|---|
| Canonical SQLite state + FTS5 | TESTED | `health.run_all()` → `database: integrity=ok, fts=on`. 248 tests pass. |
| Session logging / durable index | TESTED | `sessions.start()` → `SES-A2475EE4` on a clean `AION_HOME`. |
| Task creation / state transitions | TESTED | `tasks.create()` → `TASK-92725768`; `tasks.update(status=…)` verified. |
| Checkpoint + crash/resume | TESTED | `resume.boot()` returns `health`/`resume`/`steps`/`previous_next_action`. |
| Backup + **real restore** | TESTED | `backup.create()` then `backup.verify()` → `{'ok': True, 'integrity': 'ok'}`. Verify genuinely extracts the archive and opens the DB — this is a real restore test, not a checksum. |
| Owner approvals | TESTED | `approvals.create()` → `A-101`; `decide()` → `APPROVED`. States PENDING/APPROVED/DENIED/EXPIRED. |
| Budget governor (spend) | TESTED | `aion_core/governor.py` (103 lines); `health` → `governor NORMAL`. |
| Resource governor (capacity) | IMPLEMENTED (off) | `feature/resource-governor` only; 16 modules; flag-gated **off** by default. Not in Q006. |
| Deterministic health runner | TESTED | 14 checks, honest failures (`shared_brain`, `secret_store`, `backup` all correctly report missing on a fresh home). |
| Skills registry | DEGRADED | 9 registered / 9 enabled, but a legacy-case migration gap breaks validation on upgraded databases (§4). |
| Skill catalog | DESIGNED | 104 catalog manifests vs 9 registered skills. The catalog is a design inventory, not live capability. |
| LearnRepo (queue/health) | TESTED | `health` → `learnrepo: latest=not-run, ai_calls=0`. |
| Architecture anti-duplication guard | DESIGNED (not enforcing) | Self-declaration form, manual CLI only (§5, §7). |
| Secret scanner + gitignore hygiene | TESTED (not enforced) | `./aion scan .` → clean; `.gitignore` covers `private_state/`, `*.env`, `*.pem`, `*oauth*.json`, `rclone.conf`. Nothing runs it automatically. |
| Local inference (Ollama) | IMPLEMENTED | `worker.ollama_available()`, `run_ollama()`. Not installed here; degrades to class B as designed. |
| Drive bridge | IMPLEMENTED / partially LIVE | rclone-based (`bridges/drive_bridge.py`). **Drive reads verified live from this session** (§9). Uploads unverified here. |
| OpenClaw integration | UNKNOWN | Referenced in `README.md`, `scripts/*.sh`, `whatsapp_bridge.py`, `cli.py`. Could not verify a live gateway from this environment. |
| GitHub Actions / CI | **ABSENT** | No `.github/` on `main`, Q006, `feature/resource-governor`, or `claude/fable-deploy-setup`. |
| Branch protection on `main` | **ABSENT** | GitHub API: every branch `"protected": false`. |
| Mac portability | ABSENT (≈DESIGNED) | Exactly one line repo-wide mentions darwin: `learnrepo.py:555`. All 9 service units are systemd. |
| Mark-2 (Linux) deployment | DEPLOYED (historical claim) | 9 systemd units exist. Live state not verifiable from here — UNKNOWN as of now. |

---

## 2. Branch-divergence map

18 remote branches, measured with `git rev-list --left-right --count origin/main...<branch>`.

**Verified structural facts:**
- Q000→Q006 is a **strictly linear stack** (`git merge-base --is-ancestor` passed on all 7 links).
- Q006 HEAD **equals** `04_HANDOFF_POINTERS.json:verified_base_commit`. The pointer is accurate.
- `feature/learnrepo-queue-health` (`75459ad`) is **already inside** Q006 — not separate work.
- `feature/resource-governor` (`1d6aa7e`) is **not** inside Q006.
- `claude/aion-whatsapp-control-1seild` is a **strict ancestor** of `claude/fable-deploy-setup-mc5nr6` — zero unique content.
- `planning/opus-fable-20260916` = Q006 + 5 planning-only commits (docs only).

| Branch | Ahead/Behind main | Verdict | Reason |
|---|---|---|---|
| `feature/skill-system-q006-architecture-guard` | 8 / 0 | **KEEP** — integration base | Linear on main, 248 tests pass, contains all of Q000–Q005 + learnrepo-queue-health. |
| `feature/resource-governor` | 1 / 0 | **KEEP (needs conflict resolution)** | Disciplined, flag-gated-off, additive. But collides with Q006 on `aion_core/learnrepo.py` (§3). |
| `claude/lucyos-architecture-audit-4o4q83` | 11 / 0 | **NEEDS REVIEW** | Linear on main. Carries `docs/architect/*` planning artifacts that duplicate this `.lucy/` planning surface (§3), plus real code (`recall/`, `util.py`, `worker.py` +156/−40). Split it. |
| `feature/skill-system-q000…q005` | 2–7 / 0 | **SALVAGE → then delete** | Intermediate stack states, fully contained in Q006. Keep only as history. |
| `feature/learnrepo-queue-health` | 1 / 0 | **SALVAGE → then delete** | Already inside Q006. |
| `claude/fable-deploy-setup-mc5nr6` | 32 / **31** | **NEEDS REVIEW (salvage selectively)** | 92 files, 8,235 insertions, 31 commits behind. Adds `PROJECTS/`, `deploy/`, SEVAACONNECT tests. Too stale to merge wholesale; cherry-pick by capability. |
| `claude/aion-whatsapp-control-1seild` | 28 / 31 | **REJECT** | Strict ancestor of the above. No unique content. |
| `arch/lucyos-interface-m-a` | 0 / 2 | **REJECT (already merged)** | Zero ahead. |
| `candidate/mark2-loop-v1.2-20260908` | 1 / 26 | **REJECT** | One manifest file, 26 behind. |
| `backup/pre-mark2-loop-v1.2-20260908` | 0 / 26 | **KEEP as archive tag** | Pure backup, zero ahead. Convert to a tag. |
| `feature/lucyos-aion-handoff` | 1 / 37 | **REJECT** | 37 behind; superseded `Projects/LucyOS/OS/*` docs. |

**Recommended integration order:** `main` → Q006 → resolve the `learnrepo.py` collision → `feature/resource-governor` → split and land the useful half of `claude/lucyos-architecture-audit-4o4q83`.

---

## 3. What already works and must be preserved

The brief said to assume the existing AION architecture has value until evidence
disproves it. **The evidence confirms the value.** I exercised the kernel
directly on a clean `AION_HOME` and it behaved correctly:

- Canonical SQLite + FTS5, integrity clean.
- Session logging, task lifecycle, checkpoint/resume all functioning.
- **Backups that actually restore.** `backup.verify()` extracts the archive and
  opens the database. Most systems this age do not have a real restore test.
- Approvals with a genuine state machine.
- A health runner that **reports honest failure** — on a fresh home it correctly
  says `shared_brain` is missing, `secret_store` is not created, `backup` has no
  directory. It does not fake success. That is the single strongest signal in
  this codebase.
- Secret hygiene: comprehensive `.gitignore`, a working scanner, and a
  `drive_bridge.py` that deliberately never prints rclone stderr because it may
  contain OAuth material.
- The `resource_governor` integration is textbook-careful: flag-gated off,
  wrapped so it cannot break the worker loop, purely additive.

**Do not replace any of this.** The gaps below are about *enforcement and
integration*, not about the kernel being wrong.

---

## 4. What is degraded or broken, with root-cause confidence

### 4.1 Skill-registry case migration — DEGRADED, root cause **HIGH confidence**

The `f0` → `F0` mismatch reported in `00_READ_ME_FIRST.md` is **real, reproduced,
and does not self-heal.**

```
clean registry errors: []
after lowercase f0 injected: ['ai.cloud:invalid-cost']
after ensure_defaults re-run: ['ai.cloud:invalid-cost']    # ← still broken
```

Root cause: `skills.register()` normalizes with `.upper()` on write
(`skills.py:115-118`), and manifest validation compares case-insensitively
(`skills.py:270`), but `validate_registry()` compares **case-sensitively**
(`skills.py:203`), and the compatibility migration in `ensure_defaults()`
(`skills.py:163-164`) only maps the *word* labels `none/free/local/external`.
A pre-Q005 row holding a correctly-named but lowercase class code is therefore
never normalized and fails validation permanently.

**Why CI would never have caught this:** the 248 tests always start from a clean
database. The bug only exists on an *upgraded* database — i.e. the live Mark-2
one. This is the most important structural lesson in the audit: **LucyOS has no
migration test at all.**

### 4.2 The prepared fix in Drive is too narrow — verified

`MARK2_SHARED/…/LUCYOS_STEP1_F0_MIGRATION_FIX.patch` adds `'f0'` to the `IN`
list and a regression test. It fixes the reported symptom but not the bug class.
I injected three other legacy-case values the patch would not heal:

```
errors after ensure_defaults: ['ai.cloud:invalid-cost',
                               'core.health:invalid-data',
                               'core.state:invalid-risk']
```

`risk_class`, `data_class` and `priority` have **no normalization at all**, and
`cost_class` codes other than `f0` remain broken. Recommend a generic
normalization (`SET x=upper(x) WHERE x <> upper(x)` for all four columns, keeping
the existing word-label mappings) plus a migration test. Still a small,
deterministic change — suitable for Sonnet, but it should be scoped as the
**class** of bug, not the one reported instance.

### 4.3 Drive uploads

Reads verified working live from this session (§9). Upload failure reported
historically on Mark-2 is **UNVERIFIED here**. Given the bridge shells out to
`rclone`, the likely cause is rclone auth scope or a remote permission — a
configuration issue, not a code defect. Confidence: LOW-MEDIUM, needs Mark-2 access.

---

## 5. Duplicate architecture / control-plane risks

### 5.1 P0 — `aion_core/learnrepo.py` is two unrelated modules at one path

| Branch | Lines | What it actually is |
|---|---|---|
| `main` | — | absent |
| `feature/resource-governor` | 78 (`524abbe2…`) | third-party **research registry**: RESEARCH → SANDBOX → SECURITY_REVIEW → BENCHMARK → OWNER_APPROVAL, table `research_targets` |
| `feature/skill-system-q006…` | 669 (`38d16b28…`) | **maintenance queue + deterministic health runner** with single-node leases |

Merging these two branches produces a hard add/add conflict, and the two
concepts are not reconcilable by merge — they are different features that
collided on a name. A **third** meaning of "LearnRepo" exists as the
`.claude/skills/learnrepo/` capability-acquisition skill on
`claude/lucyos-architecture-audit-4o4q83`.

**Fable must name these three things distinctly before any integration.**

### 5.2 P1 — Two governors with no precedence contract

`governor.py` (spend/₹: NORMAL…STOP, demotes cost class) and
`resource_governor/` (capacity in tokens — UNKNOWN…AVAILABLE) both gate *which model
class runs work*, on different axes. Neither is wrong; the new one is correctly
flag-gated off. But **nothing defines which wins** when spend says SHIFT-DOWN and
capacity says AVAILABLE, or vice versa. That is a Fable decision, not a coding task.

### 5.3 P1 — `aion_core/worker.py` modified by all three live lineages

Q006 (+12), `feature/resource-governor` (+28),
`claude/lucyos-architecture-audit-4o4q83` (+156/−40). Any integration order
requires a real merge on the critical execution path. Sequence deliberately.

### 5.4 P2 — Two planning surfaces

`docs/architect/*` (on the claude audit branch, including
`LUCYOS_ARCHITECT_EXECUTION_PACKAGE.md` and `05_LOW_MODEL_TASK_QUEUE.md`) is a
prior, parallel attempt at exactly what `.lucy/planning/` + `.lucy/authority/` +
`.lucy/execution/` now do. Two competing task queues and two architect packages
is the same duplicate-control-plane failure, one level up. Pick one; archive the other.

---

## 6. CI gap and the clean-machine acceptance gates needed

**There is no CI anywhere.** Verified: no `.github/` tree on `main`, Q006,
`feature/resource-governor`, or `claude/fable-deploy-setup`. The historical claim
was narrower than reality — it is not just `main`.

Consequence: contract `03` requires "a deterministic CI verifier" before Sonnet
begins bulk coding. **That verifier has no host.** This is the single biggest
blocker to the entire Opus → Fable → Sonnet → Codex plan.

**Good news:** a well-built workflow already exists — in Drive, never committed:
`MARK2_SHARED/…/LUCYOS_CODING_AGENT_HANDOFF_2026-09-16/lucyos-ci.yml`. I read it.
It covers a 3.9/3.11/3.14 matrix, `compileall`, `./aion scan .`, the full unit
suite, and a clean-bootstrap job doing init → seed → health → backup →
`--verify-only` → fresh-process `boot` → second health. That is a genuinely good
clean-machine gate and should be **adopted as the baseline, not rewritten**.

It is missing exactly three things, all of which this audit shows are needed:

1. **A migration/upgrade test.** Seed an *old-shape* database, run the upgrade
   path, assert `validate_registry() == []`. Without this, §4.1-class bugs stay
   invisible forever.
2. **An authority/protected-path verifier** comparing the executor branch against
   files at `FABLE_FREEZE_SHA` (§7).
3. **An architecture-guard invocation**, so the Q006 guard actually runs in the
   pipeline instead of only when a human types the command.

---

## 7. High-model → low-model hierarchy: gap analysis

**Finding: the hierarchy is currently prompt-only. It is not enforced by anything.**

Four independent verifications:

1. **The guard is a self-declaration form.** `architecture.py` validates that a
   *proposal dict* contains the right booleans, then blocks if the proposer
   declared `new_scheduler: true`. It never inspects code or a diff. A worker
   that adds a second scheduler and writes `new_scheduler: false` gets `PASS`.
2. **The guard is manually invoked.** The only caller is the CLI subcommand
   `aion architecture-check <path>` (`cli.py:511-514`). No worker hook, no commit
   hook, no CI.
3. **No CI exists** to host any verifier (§6).
4. **`main` is unprotected** — GitHub API reports `"protected": false` for every
   branch, including `main`.

**Empirical proof the gap is real, not theoretical:** a second governor and a
second `aion_core/learnrepo.py` both landed on branches without the
anti-duplication guard ever firing. The guard did not fail; it was never asked.

Every "MUST NOT" in contract `03` — *must not merge into main, must not add a
duplicate scheduler, must not weaken security gates* — is today enforced only by
the executor's willingness to comply.

### Recommended deterministic enforcement (ordered by leverage)

1. **Enable branch protection on `main`** (require PR + passing checks, no direct
   push). This is a repository setting, needs no code, and closes the largest
   hole. **Owner action, one minute.**
2. **Commit `lucyos-ci.yml`** so checks exist to require.
3. **Add a protected-path verifier** driven by `FABLE_FREEZE_SHA`, comparing the
   executor branch to files *at that SHA*, exactly as contract `03` specifies.
   Diffing against the freeze SHA rather than a manifest is correct — a manifest
   is itself editable by the model it constrains.
4. **Make the guard read reality, not a declaration.** At minimum, have it check
   the diff for new scheduler/daemon/DB entry points instead of trusting booleans.
   A self-declaration form is an honesty aid, not a control.
5. **Run the secret scanner in CI.** It works and it is clean today; nothing
   currently guarantees it stays that way on a public repository.

---

## 8. Security and authority-boundary findings

| # | Finding | Severity | Evidence |
|---|---|---|---|
| S1 | Repository is **public** | **P0** | GitHub API: `"private": false`, `"visibility": "public"`, `allow_forking: true`, 9 open issues. Re-verified today, not inherited. |
| S2 | `main` is **unprotected** | **P0** | GitHub API: `"protected": false` on all 18 branches. Any actor with push rights — including a lower-cost model — can push straight to `main`. |
| S3 | No CI ⇒ no automated secret scan | **P0** | §6. The scanner exists and passes; nothing enforces it. On a public repo, one careless commit is permanent exposure. |
| S4 | Authority contract is unenforced | **P0** | §7. |
| S5 | Secrets hygiene itself is **good** | (positive) | `.gitignore` covers `private_state/`, `.env*`, `secrets.env`, `*.pem`, `*.key`, `id_ed25519*`, `rclone.conf`, `*oauth*.json`. `./aion scan .` clean. No tracked secret files. |
| S6 | `.secretscanignore` grew by one entry on `feature/resource-governor` | INFO | `tests/test_resource_governor_checkpoint.py` — a legitimate test fixture. Benign, but every addition narrows scanning and should stay visible in review. |
| S7 | Drive bridge suppresses rclone stderr deliberately | (positive) | `drive_bridge.py:151` — avoids leaking OAuth material into logs. |
| S8 | `assigned_secret` rule false-positives on ordinary prose and code | P2 | It fired twice during this audit: on `token_budget=token_budget` (a same-name kwarg) and on the prose `tokens: UNKNOWN…AVAILABLE`. The `_IDENTIFIER` exemption (`security.py:50`) only excuses ALL-CAPS or dotted values, not plain snake_case. Harmless alone, but friction pushes people toward `.secretscanignore` entries, and every entry stops a real file being scanned. Widen the exemption rather than the ignore list. |

**S1 + S2 together are the urgent pair.** A public repository with an
unprotected default branch, holding a personal AI operations hub, is the highest
residual risk in this audit. Neither requires code to fix.

---

## 9. Drive / OpenClaw / Mark-2 / Mac readiness

**Drive — reads LIVE_VERIFIED from this session.** I listed `MARK2_SHARED`,
located `LUCYOS_OPUS_FABLE_PLANNING_2026-09-16` (created today, matching the
pointer), and successfully downloaded two files. The read path works.
Uploads: UNKNOWN from here.

Two artifacts sit in Drive that should be in git (§6, §4.2): `lucyos-ci.yml` and
`LUCYOS_STEP1_F0_MIGRATION_FIX.patch`. **Drive is being used as a delivery
mechanism for repository content.** That is the boundary violation to fix:
Drive is collaboration/archive; code and CI belong in git.

**OpenClaw — UNKNOWN.** Referenced across `README.md`, `TOMORROW.md`,
`scripts/install_services.sh`, `scripts/build_loop.sh`, `whatsapp_bridge.py`,
`cli.py`. I could not verify a live gateway from this environment and will not
infer function from filenames. Needs Mark-2 access to classify.

**Mark-2 (Linux) — the real target.** 9 systemd units including
`mark2-drive.service/.timer` and `mark2-desktop-commander.service`.

**Mac — effectively ABSENT.** Exactly one line repo-wide is Mac-aware:
`learnrepo.py:555` returns `"launchd"` for darwin. It only *names* the scheduler;
there are no launchd plists and no Mac install path. Every deployment unit is
systemd.

This matters beyond deployment: recent work on this repo targets a **future
Mac-mini-hosted local recall engine**. That target currently has **no portability
substrate at all**. Treat "Mac mini readiness" as a P1 work item, not a
packaging detail.

---

## 10. P0 / P1 decisions Fable must make

**P0-1 — Namespace collision.** Three things are called "LearnRepo". Name them
distinctly (suggestion: `learnrepo.py` = maintenance/health queue, `research_registry.py`
= third-party candidate pipeline, `.claude/skills/learnrepo/` = the acquisition
skill) and decide which branch renames.

**P0-2 — Enforcement substrate.** Approve: branch protection on `main`, commit
`lucyos-ci.yml`, add the `FABLE_FREEZE_SHA` protected-path verifier. Until this
exists, **no Sonnet bulk-coding phase should start** — contract `03` explicitly
predicates the Sonnet phase on a deterministic verifier that today has no host.

**P0-3 — Repository visibility.** Public or private? If it stays public, S3
becomes mandatory before any further work.

**P0-4 — Integration order** for Q006 / `feature/resource-governor` /
`claude/lucyos-architecture-audit-4o4q83` across the shared `worker.py`.

**P1-1 — Governor precedence.** Which governor wins, on which axis, and does
`resource_governor` stay flag-gated off after integration?

**P1-2 — Planning-surface consolidation.** `.lucy/` or `docs/architect/`. Not both.

**P1-3 — Migration-testing policy.** §4.1 proves clean-DB tests cannot see
upgrade bugs. Decide that every schema/enum change ships with a migration test.

**P1-4 — Mac-mini portability.** Own it as a work item or explicitly defer it.

**P1-5 — `claude/fable-deploy-setup-mc5nr6`** (32 ahead / 31 behind, 8,235
insertions): salvage which capabilities, or reject wholesale?

---

## 11. P2 task classes to delegate to Sonnet / local models

Bounded, mechanical, each with a clear acceptance test. **None may start before
P0-2 is in place.**

1. Generic case-normalization migration for `cost_class`/`risk_class`/`data_class`/
   `priority` + migration regression test (§4.2). The Drive patch is a starting
   point but must be widened to the bug class.
2. Commit `lucyos-ci.yml` as-is, then add the three missing gates (§6).
3. Rename modules per P0-1 once Fable decides the names.
4. Delete/tag the REJECT and merged-SALVAGE branches per §2.
5. Write the `launchd` equivalents of the 9 systemd units (only after P1-4).
6. Move `lucyos-ci.yml` and the F0 patch out of Drive into git (§9).
7. Mechanical merge-conflict resolution on `worker.py` **after** Fable fixes the order.

---

## 12. WHAT NOT TO BUILD

- **Do not build a third LearnRepo.** Two already collide.
- **Do not build a third governor.** Define precedence between the existing two.
- **Do not build a second task queue or architect package.** `docs/architect/05_LOW_MODEL_TASK_QUEUE.md`
  and `.lucy/execution/SONNET_TASK_QUEUE.md` are the same idea twice.
- **Do not replace the AION kernel.** It was exercised directly and works (§3).
- **Do not build a bespoke CI system.** A good workflow already exists; commit it.
- **Do not write a manifest-based authority checker.** Contract `03` is right:
  verify against `FABLE_FREEZE_SHA`, because a manifest is editable by the model
  it is supposed to constrain.
- **Do not add a second canonical store, scheduler, secret store or approval system** —
  the existing ones work.
- **Do not treat the declaration-form guard as enforcement.** Either make it read
  diffs or stop describing it as a control.

---

## 13. Exact evidence paths and commits used

- Audited base: `2b59aea7d785bbc42139dcb361834bb48ae158a3` (Q006 HEAD; matches `04_HANDOFF_POINTERS.json`).
- `main` @ `33e4cedf18d79872bf45db80f5f04dd7a3e35ed9`; `feature/resource-governor` @ `1d6aa7e`; `feature/learnrepo-queue-health` @ `75459ad`.
- Divergence: `git rev-list --left-right --count origin/main...<branch>` over all 18 branches; `git merge-base --is-ancestor` for stacking.
- Blob identity: `aion_core/learnrepo.py` = `524abbe2…` (resource-governor, 78 lines) vs `38d16b28…` (Q006, 669 lines).
- Test suite: `python3 -m unittest discover -s tests -t . -q` → **Ran 248 tests … OK**.
- Live probes on a clean `AION_HOME`: `health.run_all()`, `backup.create()/verify()`, `sessions.start()`, `tasks.create()/update()`, `resume.boot()`, `approvals.create()/decide()`, `skills.validate_registry()`.
- Code: `aion_core/skills.py:115-118, 163-164, 203, 270`; `aion_core/architecture.py`; `aion_core/cli.py:511-514`; `aion_core/governor.py`; `aion_core/worker.py:106-124, 254-309`; `bridges/drive_bridge.py:151`; `learnrepo.py:555`.
- GitHub API: `list_branches` (all `protected: false`), repo metadata (`private: false`, `visibility: public`).
- Drive: `MARK2_SHARED` (`17lO5xq8…`), `LUCYOS_OPUS_FABLE_PLANNING_2026-09-16` (`1Zw7DhlE…`), `lucyos-ci.yml` (`1fVhjrWl…`), `LUCYOS_STEP1_F0_MIGRATION_FIX.patch` (`14LWP5Uu…`) — both downloaded and read.

---

## 14. Uncertainties and owner information still needed

1. **Is the repository intentionally public?** (S1) — blocks P0-3.
2. **Mark-2 live state** — is Q006 still running there? Is the DB carrying the legacy-case rows from §4.1? Not verifiable from this environment.
3. **Drive upload failure** — needs a Mark-2 rclone check; I could only verify reads.
4. **OpenClaw** — is the loopback gateway expected to be live? Currently UNKNOWN.
5. **`claude/fable-deploy-setup-mc5nr6`** — is SEVAACONNECT in scope now, or parked? Determines salvage vs reject.
6. **Mac mini** — real near-term target, or aspiration? Determines P1-4 priority.
7. **Who may push to `main`** today? Needed before designing protection rules.

---

## 15. FABLE START HERE

You are inheriting a **working kernel with no enforcement layer.**

**The kernel is real.** I exercised it directly: canonical SQLite + FTS5,
sessions, task transitions, checkpoint/resume, approvals, and backups that
genuinely restore. Health reporting is honest — it tells the truth about what is
missing. 248 tests pass at `2b59aea`. Preserve this; do not redesign it.

**The enforcement layer does not exist.** Not weak — absent:
- no CI on any branch;
- `main` unprotected;
- the anti-duplication guard is a self-declaration form invoked only by hand;
- the repository is public.

Contract `03` predicates the Sonnet phase on a deterministic verifier. **That
verifier has nowhere to run.** Your first decision is therefore not architecture,
it is substrate: protect `main`, commit the `lucyos-ci.yml` that is already
written and sitting in Drive, and add the `FABLE_FREEZE_SHA` protected-path
check. Until then, every authority rule is honor-system — and we have proof it
does not hold, because a second governor and a second `aion_core/learnrepo.py`
both landed without the guard ever firing.

**Three things collide before any merge:**
1. `aion_core/learnrepo.py` is two unrelated modules at one path (78-line research
   registry vs 669-line health queue). Hard conflict. Rename before integrating.
2. Two governors (spend vs capacity) with no precedence rule.
3. `worker.py` is touched by all three live lineages.

**One lesson worth generalizing:** the `f0`→`F0` bug is invisible to the test
suite because tests always start from a clean database, while the bug only exists
on an upgraded one. The patch already prepared in Drive fixes the one reported
value; I verified it leaves `risk_class`, `data_class`, `priority` and the other
cost codes broken. **LucyOS has no migration test. Add that policy, not just that patch.**

**Integration order:** `main` → Q006 (KEEP, the base) → resolve the `learnrepo.py`
collision → `feature/resource-governor` (KEEP, flag-gated off) → split
`claude/lucyos-architecture-audit-4o4q83` (code useful, planning docs duplicate
this surface). Reject `claude/aion-whatsapp-control`, `arch/lucyos-interface-m-a`,
`candidate/mark2-loop`, `feature/lucyos-aion-handoff`.

**Do not** build a third LearnRepo, a third governor, a second task queue, or a
bespoke CI. **Do** decide repository visibility before anything else touches this repo.
