# 02 — Architecture Decision Records (LucyOS)

Status legend: ACCEPTED (act on it) · PROVISIONAL (act on it, revisit at the named gate) · DEFERRED (do not build; trigger named).
Every ADR names the evidence it rests on. Re-open an ADR only when new evidence invalidates that evidence.

---

## ADR-01 — AION remains the LucyOS kernel. KEEP and HARDEN. (ACCEPTED)

**Decision.** `aion_core` is the policy/state kernel. No rewrite. No framework replaces it.
**Evidence.** 207 tests pass in a clean environment; stdlib-only; already implements canonical SQLite state, evidence-gated completion, deterministic owner commands, budget governor with downshift-only semantics, idempotent packet ingestion, resume-without-replay. These are exactly the properties a control plane needs and the parts frameworks do badly.
**Consequences.** Engineering effort goes into (a) the execution boundary, (b) backups, (c) service identity, (d) telemetry — not into new orchestration.
**Rejected.** Rebuild on LangGraph/OpenClaw/Temporal/n8n; "Lucy as a persistent agent"; multi-agent hierarchy.

## ADR-02 — The controller is "the hardened Linux host running AION". Today that is Mark-2. Buy no hardware until the Phase-1 exit gate. (PROVISIONAL, revisit at Phase-1 gate ≈ 60–90 days)

**Decision.**
1. Keep Mark-2 (DigitalOcean, Ubuntu 24.04, 2 vCPU/4 GB) as the control plane for Phases 0–3.
2. Harden it (non-root service user, remove remote-shell services, off-host encrypted backups, firewall) rather than migrating.
3. Re-decide at the Phase-1 gate using measured data: (i) data classification of what LucyOS actually stores, (ii) measured RAM/CPU, (iii) measured local-inference value, (iv) VPS bill.
4. If an on-premises controller is then justified, the default is a **fanless Linux mini-PC** (≈₹35–60k, 32 GB, 1 TB NVMe) because every unit file, lock, path and sandbox in the repo is Linux/systemd. A Mac mini is acceptable **only as an owner-preference choice** (macOS ecosystem, FileVault/Secure Enclave), at base 24 GB, never Pro-tier; it costs a launchd port and loses systemd sandboxing.
**Why this challenges the research.** The research asked "used M4 or new M6?" The right question is "does a ₹2,100/month VPS that already runs the kernel need replacing?" Over 36 months the VPS costs roughly what a used M4 costs, includes weekly image backups, needs no UPS/electricity/physical security, and the controller workload is <1 GB RAM of Python. The only strong argument for on-prem is data residency/privacy of client documents — which is a data-store decision, not a controller decision (see ADR-10: documents can live on-prem while the control plane stays where it is).
**Hard triggers to buy on-prem hardware:** owner classifies client contracts/finance as "must not leave premises"; or sustained RAM >3 GB / CPU >70% on Mark-2 after tuning; or VPS costs exceed ₹4k/month for the controller role; or local inference proves >30% cheaper per accepted result than API for a real recurring workload (ADR-08 telemetry).
**Rejected.** M5 Pro / 64 GB; any purchase before backups and boundary exist; 4× RTX 2060; RTX 3060 "because cheap".

## ADR-03 — SQLite stays canonical. Add FTS5, integrity checks and a portable export. Postgres only on named triggers. (ACCEPTED)

**Decision.** One SQLite file in WAL mode remains the source of truth. Add: `documents` + `claims` + `sources` tables with FTS5; nightly `PRAGMA integrity_check` + `quick_check` on the live DB (already done on backups); `aion export`/`import` schema-versioned manifest (LQ-09).
**Postgres triggers (any one):** a second writer host; sustained write contention (>~30 writes/s or `SQLITE_BUSY` errors weekly); DB >10 GB; a multi-user business app with concurrent human users; need for row-level security per company.
**Rejected now.** Managed Postgres, pgvector, standalone vector DB. Embeddings only after an FTS5 recall test on a real question set fails (measure first: LQ-13 includes the test harness).

## ADR-04 — No Temporal, n8n, Kubernetes, LangGraph-as-kernel, LiteLLM gateway, MCP-everywhere. (DEFERRED with triggers)

| Component | Trigger to reconsider |
|---|---|
| Temporal | >5 long-running multi-step workflows with cross-host activities whose failure recovery the AION task engine cannot express; or resume bugs recur after failure-injection tests. |
| n8n | >10 third-party SaaS integrations maintained by hand AND the owner wants non-programmer editing. Even then: n8n behind the broker, never holding master credentials, never canonical. |
| Kubernetes | Never at this scale. |
| LangGraph | Only inside an ephemeral worker that genuinely needs an interruptible graph; never for control flow across tasks. |
| LiteLLM-style gateway | Only when ≥3 providers are in active rotation and per-provider adapters become the maintenance bottleneck. |
| MCP | Only where it eliminates real adapter code; each MCP server gets a capability manifest like any tool. |

## ADR-05 — OpenClaw and every third-party runtime is a transport/tool adapter, never an authority. The Desktop Commander service is removed from the architecture. (ACCEPTED)

**Decision.** OpenClaw owns no credentials beyond its own channel, no shell, no approval semantics, no canonical state. `mark2-desktop-commander.service` (root remote terminal via npm relay) is incompatible with every trust boundary in this design and must be disabled (OD-03, owner action). Any future remote administration is owner-only SSH with keys, over Tailscale, to a separate admin account.
**Evidence.** Code already treats OpenClaw as transport; only the agent-registry metadata and the desktop-commander unit contradict it.

## ADR-06 — Capability broker + GREEN/AMBER/RED policy engine is the first engineering build. Approvals become typed, scoped, expiring objects. (ACCEPTED)

**Design (deterministic, no model in the loop):**
```
task ──► manifest (what this task may touch) ──► broker.check(action) ──► ALLOW / NEEDS_APPROVAL(band=RED) / DENY
                                                       │
                                     policy root (owner-owned, read-only to lucy user, hash-verified at boot)
```
- **Manifest** per task/worker: `fs_read[]`, `fs_write[]`, `net_allow[]` (hostnames), `grants[]` (named credential handles, never values), `money_max_inr`, `shell` (`none|argv-allowlist`), `expires_at`, `band` (GREEN/AMBER/RED). Schema in the execution package §6.
- **Broker** is the only code path that (a) runs commands, (b) opens network connections on behalf of workers, (c) injects credentials. Workers receive handles; the broker resolves handle→value at call time from the secret store and never returns the value into model context.
- **Bands.** GREEN executes; AMBER executes only if a named standing policy (with budget counters) passes; RED creates an approval object and parks the single task.
- **Approval object v2:** `approval_id`, `action_type` (enum), `target`, `scope_json` (amount cap, hosts, paths, counts), `band`, `requested_by`, `evidence_ref`, `expires_at`, `nonce`, `decided_by`, `decided_via` (channel), `decision_hash`. A decision is valid only if: channel authenticated as owner, approval not expired, and the executed action matches `scope_json`. "APPROVE A-101" from an unauthenticated adapter is ignored.
- **Self-modification law.** Files under `policy/` and the broker code are owned by the owner-admin account; the `lucy` service user has read-only access; boot verifies the policy hash against a value the owner set. A worker cannot allowlist a command, change a band, or raise a budget. `aion allow-command` becomes owner-only (requires admin invocation).
**Evidence.** `worker.check_command` is a prefix allowlist before `shell=True`; `agents.allowed_tools` is never read; `approvals.decide` trusts any `by`.

## ADR-07 — The office Radeon PC is a compute appliance. It joins only through an inference endpoint plus one dedicated folder, after a qualification gate. (ACCEPTED)

**Boundary.** Host firewall permits port 11434 (or llama.cpp server port) from the controller's Tailscale identity only. A dedicated low-privilege OS account runs the server. Exactly one directory (`AI_WORKSPACE/{in,out,models,tmp}`) is shared. No RDP/SSH/WinRM/SMB to LucyOS. LucyOS holds no credential for that machine.
**Gate (LQ-12).** identify GPU+OS → check AMD support matrix → isolated runtime install → serve one 7–8B and one 14B-class model → measure tokens/s, quality on a fixed 30-item task set, power draw, thermals → 24 h soak → isolation audit (nmap from controller shows only the endpoint) → PASS/FAIL recorded as evidence. FAIL ⇒ cloud API remains class A/B; no NVIDIA purchase.
**Data class.** Only data classed INTERNAL or lower goes to the appliance until the isolation audit passes; CONFIDENTIAL never goes to cloud GPUs.

## ADR-08 — Model routing: "class A" means cheapest *validated* executor, not "local". Telemetry decides, not ideology. (ACCEPTED)

**Decision.** Keep the DET→A→B→C→D ladder, but bind class A to whichever executor has the best measured `cost_per_accepted_result` for the task kind. On Mark-2 today (CPU, 0.5B–1.5B models) class A should default to the cheap cloud model with deterministic validation; Ollama stays enabled only for kinds that pass a quality test. After Radeon qualification, re-measure.
**Required telemetry per model call (extend `model_usage`):** `task_kind`, `accepted` (bool, set when the task later completes with evidence), `human_corrected` (bool), `latency_ms`, `input_tokens`, `output_tokens`, `cost_inr`, `retries`, `validation_result`. Monthly report: cost per accepted result by kind × model.
**Routing inputs (add to task packet):** `privacy_class` (PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED), `consequence` (low/med/high), `ambiguity`, `freshness_ttl`. Rule: privacy first → capability → quality → latency → marginal cost. RESTRICTED never leaves the controller; CONFIDENTIAL may use the provider allowlist only.
**Cache.** Key = sha256(task_spec_version + input_hash + policy_version + model_id + prompt_version). Never cache approvals, balances, health, or anything with `freshness_ttl` expired.

## ADR-09 — Scheduling stays deterministic: timers and events, never LLM polling. The 10-minute work timer stays but is gated. (ACCEPTED)

**Decision.** `aion-work.timer` may keep firing every 10 min because `aion work` makes zero model calls when no ready A/B task exists (verified in `worker._work_locked`). Add two gates: (1) a task whose validation fails twice is parked as NEEDS_REVIEW and is never re-planned by a model automatically; (2) a daily cap on *attempts*, not just rupees, so a free-but-useless local model cannot loop. Long-running ops must be idempotent + checkpointed (already the packet/idempotency pattern).
**Lesson encoded.** Strategy Factory's "five runs, zero commits": activity metrics are not progress metrics. The daily digest reports accepted results, not runs.

## ADR-10 — State/data architecture: eleven separated stores with explicit ownership. (ACCEPTED)

| Store | Today | Target | Owner of truth |
|---|---|---|---|
| Canonical state | `state/aion.sqlite3` | same, schema v6+ | AION |
| Raw evidence | scattered under `AGENTS/results`, `RESEARCH` | `EVIDENCE/<sha256[:2]>/<sha256>` content-addressed, immutable, with `evidence` table row | AION (write-once) |
| Document store | none | `DOCUMENTS/<company>/<project>/…` + `documents` table (hash, mime, source, classification) | AION; may live on-prem later |
| Database | SQLite | SQLite (Postgres on ADR-03 triggers) | AION |
| Source control | GitHub (public today) | GitHub private (OD-01) | owner |
| Artifacts | `OUTBOX`, `work/` | `ARTIFACTS/<task_id>/` | AION |
| Audit/event log | `events` table | `events` + nightly hash-chained JSONL export to backup | AION (append-only) |
| Search index | FTS on `memory` | FTS5 on documents/claims/memory | derived (rebuildable) |
| Model cache | none | `CACHE/<key>` with TTL | derived (disposable) |
| Backups | same-disk tar.gz | restic: local + off-host + one append-only copy | owner credentials for the final chain |
| Secrets | `private_state/secrets.env` | same file short-term; broker handles; per-service scoped tokens | owner-admin |
| Checkpoint/resume | `RESUME.md` + `meta` | same + `docs/architect/CHECKPOINT.md` for architecture work | AION / architect |

Rule: nothing business-critical exists only in a chat, a Drive file, a WhatsApp thread, or a model cache. Markdown surfaces are generated views (already true).

## ADR-11 — Backups: restic, three copies, one append-only, quarterly clean-machine restore. Lucy cannot delete the final chain. (ACCEPTED)

**Design.** Nightly: `aion backup` (existing, same-disk, fast) → restic snapshot of `AION_HOME` minus `private_state` to (1) local repo, (2) off-host repo (DO Spaces / Backblaze B2 / office disk — OD-05), (3) the off-host repo is accessed with an **append-only** credential from the controller; pruning uses a separate owner-held credential. `private_state` is backed up separately, encrypted with an owner-held key (age/sops), on a different schedule, to the same off-host target. Restore drill: quarterly, on a clean VM/container, timed; result recorded as evidence with RPO/RTO. Mark-2's DO weekly image backup stays as copy zero.
**RPO/RTO targets (initial):** canonical state RPO 24 h (nightly) → 1 h once restic runs hourly; RTO 4 h to a fresh Linux host from `scripts/install.sh` + restic restore.

## ADR-12 — Communications: keep the WhatsApp Cloud API adapter as the primary channel; web UI is canonical view; Telegram is an optional fallback, not "first". (ACCEPTED — corrects research)

**Why.** The Cloud API adapter is already implemented with HMAC-SHA256 signature verification and a single allow-listed sender; the owner lives on WhatsApp/iPhone. Replacing it with Telegram gains nothing today. Telegram (LQ-16) is worth adding only as a second independent channel for P0 alerts if WhatsApp template approval/pricing becomes friction. Voice: P0-only, later, after consent/compliance design.
**Rules.** Channel identity = command authority for GREEN commands only; RED decisions require the typed approval object and an authenticated channel (ADR-06). No secrets ever transit a channel (already enforced). Alert classes P0–P3 with digest batching for P2/P3.

## ADR-13 — Business systems: shared primitives first; the first production workflow is reversible document intake for SEVAACONNECT. (ACCEPTED)

**Primitives (one schema, all domains):** organization, person, project, document, contract, lead, opportunity, quotation, boq (versioned), invoice, payment, task, approval, event, decision, claim, source, evidence, asset, property, experiment, repository. Every row carries `company_id`, `classification`, `source_ref`, `created_by` (human/worker id), `evidence_ref`.
**First workflow.** Inbound document (email/Drive/upload) → hash + dedupe → quarantine parse (no macros, size/type limits) → classify (cheap model + deterministic validation) → extract metadata → link to project/org → create tasks/deadlines → owner digest. Zero outbound side effects. This tests broker, evidence, FTS, routing telemetry and the digest without money or commitments.
**Not permanent agents:** CA/finance, procurement, BOQ, reminders, social posting, backup, KPI, document filing, tender download, security monitor — all deterministic workflows + ephemeral reasoning on ambiguity only.
**Buy/connect, don't build:** CRM (Zoho/HubSpot/…), accounting (Tally/Zoho Books), storefront (Shopify), telephony. LucyOS keeps its own canonical mirror of the fields it reasons about, via API, with idempotent writes.

## ADR-14 — Strategy Factory / treasury: separate repo, separate credentials, evidence-only interface, no execution connector. (ACCEPTED)

LucyOS may ingest Strategy Factory *status/result packets* as evidence (read-only, via the packet format). No shared process, no shared secrets, no broker grant to any broker/exchange API. Real-capital execution, broker API creation, leverage, and promotion-rule changes are RED with a dedicated policy that LucyOS cannot hold a standing AMBER policy for. Treasury policy (cash floor, reserves, allocation ranges) is an owner-authored deterministic document; Lucy computes and proposes, never transfers.

## ADR-15 — Software factory: GitHub CI is the first deterministic gate; coding workers are ephemeral and never touch production state. (ACCEPTED)

Add `.github/workflows/ci.yml` running unittest + `aion scan` + `git diff --check` on every push/PR (LQ-03). Coding workers (Codex/Claude Code sessions) operate on branches/worktrees with no production `AION_HOME`; merge requires green CI; deploy to Mark-2 is an explicit `aion deploy <sha>` step that records previous SHA and rollback command. A green exit status is never evidence; the validation command or acceptance test is.

## ADR-16 — R&D intelligence: schema now, pipeline later (Phase 8). Deterministic change detection before any model call. (DEFERRED, schema ACCEPTED)

Create `sources` (registry with authority class, cadence, parser version) and `claims` (statement, source_id, published/observed/effective/superseded dates, jurisdiction, confidence, corroborating/contradicting refs, `model_generated`, `human_verified`) tables now so document intake and Strategy Factory packets already populate them. The fetch/diff/materiality pipeline is Phase 8.

## ADR-17 — Real Estate OS and commerce: schema reservations only; no build. (DEFERRED)

Real Estate OS is a lifecycle database whose first useful slice is versioned BOQ + document/drawing revision integrity — which the shared primitives already cover. Commerce/dropshipping: no subsystem until a manual/semi-manual pilot shows positive contribution margin on real orders; LucyOS's role is the unit-economics ledger and experiment record.

## ADR-18 — Observability: the events table is the audit trail; add tamper evidence and owner-facing alert classes. (ACCEPTED)

Nightly hash-chained export of `events` (LQ-17); `aion health --deep` remains the health source; alerts classified P0 (immediate, both channels), P1 (immediate message), P2 (daily digest), P3 (dashboard only). Budget alerts at 50/80/100% of each cap. Metrics to track from day one: accepted results/day, cost per accepted result, owner interventions/day, open errors age, backup age, restore drill age.

## ADR-19 — Portability contract. (ACCEPTED)

`aion export` produces a directory with `MANIFEST.json` (schema version, hashes), the SQLite dump, evidence store, documents, policy files, and checksums; `aion import` on a fresh host recreates a working system; the quarterly restore drill uses exactly this path. Model names, provider names and host names live only in `meta`/config, never in domain logic.

## ADR-20 — Service identity: AION runs as an unprivileged `lucy` user; the owner administers from a separate admin account. (ACCEPTED)

Applies to Mark-2 now and to any future controller. `lucy` owns `AION_HOME`; cannot sudo; cannot read `/root`; unit files move to `lucy`'s user manager with linger. The owner's SSH key is distinct from any deploy key Lucy uses for GitHub. Kill switch: `aion pause` + `aion safe-mode` (existing) plus an owner-only `scripts/kill_switch.sh` that stops all `lucy` timers/services and rotates channel tokens.
