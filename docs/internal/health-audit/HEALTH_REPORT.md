# LucyOS Health Report — 2026-09-17

Auditor: high-reasoning pass per `docs/internal/LUCYOS_REPO_HEALTH_AUDITOR_TEMP.md`.
Every claim below is marked VERIFIED (observed in this session), INFERRED, or UNVERIFIED.
No repair code was pushed during this audit.

---

## Headline

**LucyOS is healthier than the branch topology suggests.** Both canonical candidates
build and pass their full suites. The single real problem is a **branch-role inversion**
that nobody recorded: `main` quietly became the canonical frozen candidate while
`integration/consolidation-20260916` kept accumulating owner work, and **neither branch
is a superset of the other**.

The reconciling merge is **conflict-free and green**, proven by real execution, not inference.

---

## 1. Repository topology — VERIFIED

| Fact | Value |
|---|---|
| Canonical-by-name integration branch | `integration/consolidation-20260916` @ `db91548` |
| Actual frozen candidate | `origin/main` @ `0720a92` ("owner: freeze supervised integration candidate") |
| `main` commits absent from integration | 27 |
| integration commits absent from `main` | 8 |
| Default branch | not set on the remote (`origin/HEAD` unresolved) |

**Finding H-1 (P3):** `origin/HEAD` is unset, so "default branch" is ambiguous to tooling
and to any fresh clone. VERIFIED.

**Finding H-2 (P1):** The branch roles inverted without any in-repo record. The roadmap
artifacts written earlier the same day (`.lucy/planning/INTEGRATION_ROADMAP*.md`) still
describe `integration/consolidation-20260916` as the target and `main` as the destination,
which is now backwards. VERIFIED, and this is the single largest source of confusion.

---

## 2. Commit and push reconciliation — VERIFIED

Full detail in `COMMIT_AND_PUSH_RECONCILIATION.md`.

**All 23 S-task branches are ancestors of `origin/main`.** Nothing was lost, nothing needs
recreating, no cherry-pick is required. Six of them (S-02, S-09, S-23, S-26, S-27, S-29)
reached `main` without ever landing on integration.

**No failed push left orphaned work.** Every task tip resolves to a reachable commit on
`main`. The earlier "blocked" PRs (S-16, S-17, S-20, S-22, S-23, S-29) were unblocked by a
real baseline fix and merged; the allowlist now contains `portability`, `guardian`,
`experiments`, `money_path`, `tempworker`, and the `S-22` override is present. VERIFIED.

**Finding H-3 (P1):** Commit `60b2dc7` ("feat: add local-first skill execution adapters",
authored by Het Patel, 2026-09-17 04:44) exists **only on integration**. It adds four new
`aion_core` modules and touches `api.py`, `cli.py`, `config.py`, `db.py`, `tasks.py`. This
is owner work that is not on the frozen candidate. It is not lost, but it is unreconciled.
VERIFIED.

---

## 3. Test health — VERIFIED by execution

| Branch / tree | Tests | Result |
|---|---|---|
| `integration` @ `db91548` | 420 | OK (1 skipped) |
| `main` @ `0720a92` | 537 | OK |
| **real merge, main ← integration** | **550** | **OK (1 skipped)** |

Neither branch is a superset: `main` has the six extra task PRs plus the S-02 salvage test
suites; integration has the four owner modules plus their tests
(`test_model_gateway`, `test_platform_resolver`, `test_semantic_recall`,
`test_usage_telemetry`, `test_sse_events`, `test_task_data_class`).

**No failing test exists on either branch.** The earlier S-20 drift failure and the S-02
portability false positive were both genuinely fixed before merge, not suppressed. VERIFIED.

---

## 4. Merge integrity — VERIFIED by execution

A real `git merge --no-ff origin/integration/consolidation-20260916` onto `origin/main`:

- **zero conflicts**
- **550 tests, OK**
- `scripts/check_portability.py`: 0 violations, 3 known exceptions (S-11, S-12), **0 stale**, 55 files, portable
- `./aion scan .`: clean
- `verify_authority.py anti-dup`: **8 violations, all from the same 4 files**

This merge was performed on a local throwaway branch (`audit/merge-probe`) and **was not
pushed**. It exists purely as evidence that the reconciliation is safe.

---

## 5. The only blocking defect — VERIFIED

`anti-dup` rejects the merged state with exactly 8 violations, reducible to two root causes:

**Root cause A — four owner modules are not allowlisted (4 violations).**
`model_gateway`, `platform_resolver`, `semantic_recall`, `usage_telemetry` are absent from
`aion_core_modules` in `.lucy/authority/HIGH_MODEL_BASELINE.json`. This is the *same class*
of omission that blocked five PRs earlier today: the code was written and tested, the
baseline was not updated alongside it.

**Root cause B — `semantic_recall.py` opens its own SQLite store (4 violations).**
Two `sqlite3.connect()` calls and two `CREATE TABLE` statements outside `db.py`.

Root cause B needs an architectural ruling, not a rubber stamp. Reading the module, this is
a **rebuildable derived vector index** (`sqlite-vec` + `fastembed`) at `index_path()`, not a
rival canonical store — which is exactly what the data-library contract permits ("indexes
rebuildable; never make an embedding DB the sole source of truth"). The `anti-dup` rule
cannot distinguish a derived index from a second source of truth, so it correctly escalates
rather than silently allowing it. **This is an owner decision, recorded in
`ISSUE_REGISTER.md` as ISSUE-002.** VERIFIED as intent by reading the code; the ruling
itself is UNVERIFIED and deliberately left open.

---

## 6. Security and authority — VERIFIED

**Finding H-4 (P2, needs owner ruling):** `aion_core/model_gateway.py` introduces outbound
HTTPS to three third-party inference providers (`openrouter.ai`, `api.groq.com`,
`api.cerebras.ai`) and reads secrets by name. Mitigations observed in the code:

- `DATA_POLICY` permits only `PUBLIC` data to leave the machine; `INTERNAL`,
  `CONFIDENTIAL` and `SECRET` are all `False`.
- `tasks.data_class` defaults to `INTERNAL` in the schema, so the default is **deny**.
- Failure limit of 3 with a 15-minute cooldown per provider.
- It is called from `worker.py:427` as an *auxiliary* path; the existing
  DET → Ollama → `cloud_command` hierarchy at `worker.py:437` is intact and unchanged.

This is competent, default-deny design. It is still a material expansion of the system's
external surface and belongs in front of the owner rather than being merged silently.

**Evidence of process, not recklessness:** learnrepo vetting manifests exist for every new
dependency under `.lucy/planning/skill-exec-20260917/` (`sqlite-vec.json`, `fastembed.json`,
`ccusage.json`, and three others), each asserting `reuse_canonical_sqlite: true`,
`reuse_task_queue: true`, `reuse_approval_engine: true`, `reuse_health: true`. VERIFIED.

**No secrets found.** `./aion scan .` is clean on integration, on main, and on the merged
tree. VERIFIED.

**Authority gates are intact.** No test was disabled, no gate weakened, no
`KNOWN_EXCEPTIONS` inflated. The portability guard reports 0 stale exceptions. VERIFIED.

---

## 7. Subsystems confirmed healthy — do not manufacture work here

Stated positively so no repair task is invented for them:

- Persistence and migrations: `upgrade-from-main-schema` CI job present; `_ADDED_COLUMNS`
  additive pattern intact; three `db.py` PRs merged sequentially without schema drift.
- Recovery: `resume.boot()` / `checkpoint()` unchanged; S-18's injection tests merged.
- Evidence gates: `worker._validate` still independently reruns `validation_command` and
  still returns `needs_review` for class A/B lacking independent validation.
- Singleton locking: `worker._execution_lock` unchanged.
- Secret scanning and redaction: unchanged and clean.

---

## 8. Health verdict

**AMBER, trending green.** Not red: nothing is broken, nothing is lost, no gate was
weakened, and the reconciling merge is proven green. Not green: the canonical branch is
ambiguous in-repo, and four owner modules cannot pass `anti-dup` until the baseline is
updated and one architectural question is answered.

Four repair tasks plus one final push task are queued in `SONNET_EXECUTION_QUEUE.md`.
Two of them are owner decisions that Sonnet must not make alone.
