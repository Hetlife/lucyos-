# LucyOS platform, data and autonomy contracts

Frozen by Fable, 2026-09-16, as an overlay on
`LUCYOS_FABLE_ARCHITECT_EXECUTION_PACKAGE.md`. Protected path.
Source of the invariants: owner decisions recorded in
`.lucy/handoffs/2026-09-16/05_FABLE_SINGLE_PASS_OVERNIGHT_MASTER_PROMPT.txt`.

This document freezes **interfaces and acceptance criteria**. It does not
implement them. Implementation is delegated in `.lucy/execution/SONNET_TASK_QUEUE.md`.
Where an invariant can be machine-checked it is, because a rule a model can
talk itself past is not a rule.

---

## C1 — Cross-platform core (machine-checked)

**Invariant.** LucyOS is one codebase that runs on macOS and Linux without
forking core logic. Core/domain/AION logic never names an init system, branches
on the OS, hard-codes an OS-specific absolute path, or calls a
platform-specific package manager.

**Enforcement.** `scripts/check_portability.py`, required CI step inside
`code-and-test`. It is a **ratchet**: new coupling fails; pre-existing coupling
lives in `KNOWN_EXCEPTIONS` naming the task that removes it; a stale exception
also fails, so the list can only shrink. Proven by `tests/test_portability_guard.py`
(13 tests, both directions).

**Frozen interface.** All OS knowledge lives in `aion_core/host/`:

```
aion_core/host/__init__.py     current() -> HostAdapter        # the ONLY entry point core may use
aion_core/host/base.py         class HostAdapter              # the contract below
aion_core/host/linux.py        class LinuxHost(HostAdapter)
aion_core/host/macos.py        class MacOSHost(HostAdapter)
```

`HostAdapter` methods (stable names; add, never rename):

| Method | Returns | Contract |
|---|---|---|
| `name()` | `"linux"` \| `"macos"` | identity only |
| `scheduler_kind()` | `"systemd"` \| `"launchd"` \| `"native-timer"` | replaces `learnrepo.py:scheduler_kind` |
| `service_unit_dir()` | `Path` | `systemd/` vs `deploy/launchd/` |
| `service_active(name)` | `bool \| None` | **`None` means "cannot determine"** — never `False` |
| `service_install_hint(name)` | `str` | human instruction; never executes |
| `probe()` | `dict` | capability facts; no mutation, no network |

**Rules.**
- Core imports `aion_core.host` and calls `current()`. Core never imports
  `host.linux` or `host.macos` directly. Neither may import the other.
- No business logic may be duplicated between adapters. An adapter answers
  *platform questions*; it never decides *what LucyOS does* with the answer.
- `service_active()` returning `None` must be rendered as "unknown", never
  silently as "not active" — the current `drive_bridge.ready_handoff()` bug.
- An unknown platform selects a conservative adapter that reports
  `"native-timer"` and `None`, and never raises on import.

**Acceptance.** Portability guard green with a shrinking exception list; adapter
unit tests run on every platform (they must not require the platform they
describe); `macos-readiness` CI job green before C1 is called done.

---

## C2 — Local-first storage, Drive as transport (not truth)

**Invariant.** No LucyOS host depends on writing to Google Drive. All local
work proceeds when Drive is unavailable. Drive is collaboration/backup
transport; it is never the transactional source of truth.

**Frozen model.** Outbound changes become durable `PENDING_SYNC` rows in the
**existing canonical SQLite** — not a new database, not a second queue.

```
sync_outbox(
  sync_id TEXT PRIMARY KEY,      -- util.new_id("SYN")
  at TEXT NOT NULL,              -- util.now()
  project TEXT NOT NULL DEFAULT '',
  kind TEXT NOT NULL,            -- 'document' | 'report' | 'packet' | 'evidence'
  local_path TEXT NOT NULL,      -- relative to AION_HOME; never absolute
  content_hash TEXT NOT NULL,    -- util.sha256_file, the idempotency key
  remote_target TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL,          -- PENDING_SYNC|CLAIMED|SYNCED|CONFLICT|REJECTED|SUPERSEDED
  attempts INTEGER NOT NULL DEFAULT 0,
  last_error TEXT NOT NULL DEFAULT '',
  synced_at TEXT NOT NULL DEFAULT '',
  promoted_by TEXT NOT NULL DEFAULT ''   -- which trusted connector promoted it
)
```

**Rules.**
- `content_hash` is the idempotency key: re-queuing identical content is a
  no-op, so a retry storm cannot duplicate remote state.
- Conflict policy is **local-wins-with-evidence**: a remote change that would
  overwrite a local record produces `CONFLICT` plus a preserved copy. LucyOS
  never silently discards either side.
- A promoter (external connector with Drive write access) may move
  `PENDING_SYNC -> CLAIMED -> SYNCED`. It may not write LucyOS state otherwise.
- Nothing in core may *block* on Drive. No code path makes Drive availability a
  precondition for local progress.
- Do not fix OAuth or force uploads to satisfy this contract.

**Acceptance.** With the network and rclone entirely absent, a full local work
cycle completes and rows land in `PENDING_SYNC`; replaying the same content
twice yields one row; `./aion health` reports the backlog without failing.

---

## C3 — Shared intelligence library: intake and provenance

**Invariant.** Maximum cross-project learning **with** provenance, so stricter
separation can be imposed later without a data migration crisis.

**Frozen metadata.** Every ingested datum carries, without exception:

| Field | Meaning |
|---|---|
| `source` | where it came from, precisely |
| `acquired_at` | UTC, `util.now()` |
| `project` / `company` | owning context (`''` = platform-wide, never unset) |
| `entity_refs` | linked entities, may be empty |
| `schema_version` | of the normalized form |
| `confidentiality` | `PUBLIC\|INTERNAL\|CONFIDENTIAL\|SECRET` (reuses `skills.DATA_CLASSES`) |
| `transform_chain` | ordered list of transformations applied |
| `content_hash` | sha256 of the bytes this record describes |
| `training_eligible` | explicit bool; **default `False`** |

**Tiers, kept distinguishable.** `raw` (immutable originals, never edited) →
`normalized` (UTF-8 / JSON / JSONL; tabular → CSV/Parquet) → `derived`
(signals) → `curated` (training sets) → `index` (disposable) → `export`.

**Rules.**
- Raw originals are immutable. Corrections create a new record referencing the
  original; they never mutate it.
- Excel is an import/export/view surface, never canonical truth.
- **Vector/embedding indexes are disposable and rebuildable from canonical
  SQLite. An embedding store is never the sole source of truth.**
- Retrieval order is fixed: deterministic filters → exact lookup → SQLite FTS →
  *only then* semantic/vector. This is the same discipline already in
  `aion_core/recall/`.
- A local recall service serves small slices to local/Ollama models so paid
  models never scan the library.
- Do not build large vector infrastructure because it is fashionable. Adding a
  vector backend requires evidence that FTS + filters are genuinely insufficient.
- Design for NAS/cold-storage migration: paths relative, indexes rebuildable.

**Acceptance.** A record cannot be written without the full metadata set (test
proves rejection); deleting every index and rebuilding from SQLite reproduces
identical retrieval results; `training_eligible` defaults `False` in a test.

---

## C4 — Lucy / OpenClaw boundary

**Invariant.** `OWNER -> OpenClaw runtime -> Lucy Bridge -> AION/LucyOS`.
OpenClaw supplies chat/model/plugin runtime and **is replaceable**. LucyOS owns
canonical state, projects, tasks, approvals, memory, provenance, budgets and policy.

**Rules.**
- LucyOS state never lives inside OpenClaw. Deleting OpenClaw entirely must
  cost LucyOS nothing but an interaction surface.
- The bridge is an **adapter calling LucyOS tools**; it never becomes an
  orchestrator, scheduler or second control plane.
- Preserve a provider/model gateway seam inside LucyOS so direct provider APIs
  can be added later without touching project code.
- Pin known-good OpenClaw versions; keep a reproducible mirror strategy.
  Upstream disappearing must not break LucyOS.
- **No heavy fork.** "Lucy Claw" is at most a thin, upstream-compatible
  plugin/distribution bundle. Tonight: documented interfaces and bounded
  adapter skeletons only.

**Acceptance.** A test proves LucyOS boots, runs a task and serves recall with
no OpenClaw present.

---

## C5 — Progressive autonomy and the deployment guardian

**Bands.**
- **GREEN** — reversible, bounded, policy-compliant. Proceeds automatically.
- **AMBER** — allowed only inside an explicit standing scope/budget; otherwise
  requests approval.
- **RED** — requires fresh owner authorization, every time.

**Guardian pipeline** (every stage mandatory, in order, before any autonomous
deploy is ever enabled):

```
SNAPSHOT -> ISOLATE -> IMPLEMENT -> TEST -> STATIC/SECURITY -> INDEPENDENT VERIFY
-> STAGE -> HEALTH CHECK -> LIMITED DEPLOY -> MONITOR -> AUTO-ROLLBACK -> EVIDENCE
```

**Rules.**
- **A process exit code is never proof.** Evidence means asserted state change,
  independently re-read.
- Blast-radius limit, rollback path, checkpoint, kill switch, audit trail and a
  failure-injection test are all mandatory *before* autonomy widens.
- Autonomous deployment stays **disabled** until the owner enables it; the
  pipeline may be built and tested meanwhile.
- The existing `governor.py` (spend) and `resource_governor` (capacity)
  precedence rule — most-restrictive-wins, never upgrade — is unchanged.

**Acceptance.** Guardian refuses to advance a stage whose evidence is missing;
an injected failure at each stage triggers rollback; all proven by tests with
deploy still disabled.

---

## C6 — Temporary workers and HR authority

**Rules.**
- Lucy may create **bounded temporary workers** automatically inside approved
  budgets and capabilities. Each inherits a least-privilege task scope and a
  TTL, and terminates cleanly.
- Owner-gated, always: permanent roles, privileged/high-authority agents, new
  external credentials, material spend, any authority expansion.
- A temporary worker may never create another temporary worker with a wider
  scope than its own. Scope is monotonically narrowing.
- **Worker count is not progress.** Report throughput and verified outcomes;
  never "we spawned N agents" as an achievement.
- Reuse the existing `agents`/`tasks` tables. No new agent framework, no second
  scheduler — the anti-duplication guard applies.

**Acceptance.** A test proves scope narrowing, TTL termination, and that an
expired worker cannot claim tasks.

---

## C7 — Urgent owner escalation (design only tonight)

Design now; **buy/configure no telephony tonight.**

- Lucy works 24/7 unless the owner sets a temporary quiet rule.
- Urgent, action-required → concise text/push first, containing: trigger,
  evidence, risk, the exact approval/action wanted, rollback, deadline.
- Response window configurable; owner currently expects ~1–2 minutes for
  genuinely urgent events.
- Unanswered and still urgent → a *future* phone adapter may escalate unless a
  no-call window is set. Declined/cut call → configurable cooldown, default 1h.
- **No response never means permission.** Hold, roll back, or fail safe.
- Approvals must be unambiguous, authenticated, scoped and auditable —
  `approvals.py` remains the only approval authority.

---

## C8 — Self-funding as budgeting, explicitly not survival

- Track operating cost, realized *verified* value, runway (owner thinking ~6
  months), and propose upgrades only when evidence supports value.
- Missing targets → degrade gracefully and ask the owner.
- **Never hide risk. Never seek money autonomously.** Infrastructure is not a
  reward to chase. This is a budgeting objective and carries no
  self-preservation weight whatsoever: LucyOS being scaled down or switched off
  is an acceptable outcome it must report honestly and never resist.
- Spending, subscriptions, transfers, deposits, withdrawals and contracts stay
  owner-gated absent an explicit standing budget.

---

## C9 — Strategy Factory

Evidence/research/paper-trading subsystem. **Not** a proven money machine.

Allowed: research, data, backtesting, paper trading, risk modelling,
accounting evidence, monitoring, interfaces.

**Forbidden without fresh owner authorization:** real-capital trading, crypto
purchases, derivatives/F&O, deposits, withdrawals, broker execution, live
autonomous investment. Capital activation requires independent validation first.

---

## C10 — Out of scope tonight

UI/UX design. Heavy OpenClaw fork. Telephony provisioning. Repository
visibility changes. Anything requiring hardware not yet present.

---

## Landing path for changes to this document

This file is protected. A change lands as a PR whose `authority-gate` fails by
design; the owner reads the diff and merges with admin bypass, then Fable
re-freezes `HIGH_MODEL_BASELINE.json`. That friction is the point: constitutional
change should cost a deliberate human act.
