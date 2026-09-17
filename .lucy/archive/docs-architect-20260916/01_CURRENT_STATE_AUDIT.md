# 01 — Independent Current-State Audit (Parts A and B)

Audit date: 2026-09-16. Auditor: high-capability architect session.
Evidence classes: VERIFIED (I ran or read it), REPORTED (a document/commit claims it), PROPOSED (design only), UNKNOWN.

This file supersedes the research package's `02_CURRENT_STATE_AND_PROGRESS.md` wherever the two differ.

---

## PART A — INDEPENDENT AUDIT OF THE RESEARCH PACKAGE

### A1. What the research got right (confirmed by my own inspection)

| Claim | My verification | Verdict |
|---|---|---|
| AION is a real deterministic kernel, not a prompt pile | Read `aion_core/*` (≈5,900 lines Python, stdlib only). Tasks, approvals, router, governor, worker, backup, packets, resume all exist and are exercised by tests. | CONFIRMED |
| "205 tests pass" | Ran `python3 -m unittest discover -s tests` in a clean Linux container, Python 3.11.15: **205 OK in 11.6 s**. | CONFIRMED (in clean env; deployment host still unverified) |
| Both repos public | GitHub API, 2026-09-16: `Hetlife/lucyos-` `"private": false`, `visibility: public`. `Hetlife/strategy-factory` `visibility: public` via session repo list. Also public: `Hetlife/paperclip` (fork), `Hetlife/claude-test`. | CONFIRMED LIVE |
| No secrets in git history | Pattern scan of full history (`git log --all -p`): only documented test fixtures (the fake GitHub token and the AWS documentation example key used in tests/test_security.py). | CONFIRMED |
| Secret handling is redaction, not brokerage | `security.py` is regex redaction + scan. `aion-bridge.service` sources the entire `secrets.env` into the process environment (`set -a; . secrets.env`). No per-task scoping. | CONFIRMED |
| Backup exists but restore is only tested to a temp dir on the same disk | `backup.py`: tar.gz into `<AION_HOME>/BACKUPS`, 14 kept, `verify()` extracts to tmp and runs `PRAGMA integrity_check`. No encryption, no off-host copy, `private_state` excluded with no separate documented backup. | CONFIRMED and WORSE than the package states (same-disk only) |
| Drive bridge is code-complete but not live | `drive_bridge.py` (532 lines) is unusually careful (hash ledger, secret filters, entropy check, fail-closed). `DRIVE_BRIDGE_RESUME.md` (2026-09-09): blocked on Google Drive API being disabled in the service-account's Cloud project. | CONFIRMED |
| Strategy Factory duplicate-day bug is a design lesson | Not re-inspected (outside repo scope); taken as REPORTED from package. | ACCEPTED AS REPORTED |
| Don't build: K8s, vector DB, Temporal now, n8n now, 4×2060, agent swarm, live trading | Independently agree; reasoning in `02_ARCHITECTURE_DECISIONS.md`. | CONFIRMED |
| Capability broker is the #1 missing subsystem | Confirmed by reading `worker.py`: the only execution boundary is a **string-prefix allowlist in front of `subprocess.run(shell=True)`**. `agents.allowed_tools` is stored in the DB but **never read by any code path** (grep: only the schema references it). | CONFIRMED, and more urgent than the package rates it |

### A2. What the research got wrong or under-weighted

1. **Mac mini as the "natural" controller is weakly justified.** The entire runtime is Linux-native: `systemd` units, `loginctl enable-linger`, `fcntl` locks, `/root/...` paths. Moving to macOS means rewriting service management (launchd), losing `ProtectSystem`/`NoNewPrivileges` sandboxing, and paying ₹50k–₹100k to run a Python-stdlib process that needs <1 GB RAM. The research's "reliability/low maintenance" argument is opinion, not evidence. See ADR-02.
2. **The research missed that the controller already exists and is running in the cloud.** Mark-2 is a DigitalOcean droplet (Ubuntu 24.04, 2 vCPU / 4 GB / 80 GB, blr1, created 4 Sep, weekly DO backups enabled) running AION **as root**. This changes the hardware question from "which Mac?" to "is a ₹2k/month VPS an acceptable controller for the data classes involved?" See ADR-02 and OD-02.
3. **The research missed `mark2-desktop-commander.service`.** The repo ships a systemd unit that runs `npx --yes @wonderwhy-er/desktop-commander@0.2.48 remote` as root with `HOME=/root` on Mark-2. That is a general-purpose remote terminal/filesystem control server exposed through a third-party relay, on the machine that holds the canonical state. It directly violates the package's own least-privilege and "no unrestricted shell" rules. See S-03.
4. **Local inference on the current host is tiny-model CPU inference.** Mark-2 has no GPU and 4 GB RAM; Ollama runs `qwen2.5-coder:0.5b` and `1.5b` (REPORTED in `DRIVE_BRIDGE_RESUME.md`). The package's routing ladder assumes a useful "class A local model". At 0.5B–1.5B parameters on CPU, the class A path is very likely **worse and slower than a ₹0.02 Haiku call** for anything beyond trivial classification. Local inference is not free here; it is low quality. See ADR-08.
5. **Approval binding is weaker than described.** `approvals.decide()` accepts any `by` string; `router.handle()` treats whatever the bridge passes as `sender` as authority. The webhook adapter defaults `sender="owner"` from an unauthenticated JSON field if `WHATSAPP_BRIDGE_TOKEN` is unset (it prints a warning and continues). Approvals have no expiry, no amount/target binding, and `cost`/`max_downside` are free text. The Cloud-API adapter does enforce an allow-listed sender. See ADR-06.
6. **The 10-minute `aion-work.timer` is a scheduled model loop** (`build_loop.sh` → `aion work --max 10`). This is exactly the pattern the package's own Strategy Factory evidence warns about ("five runs, zero commits"). It is bounded by the ₹200/day governor, which is good, but the loop's default should be event-driven with a much longer heartbeat. See ADR-09.
7. **Economics doc treats Mac purchase as "required eventually".** Not established. A DO droplet at ~₹2,100/month for 36 months ≈ ₹75k, roughly a used-M4 purchase, with zero electricity/UPS/theft risk and snapshot backups included. The decision hinges on data classification and local-inference need, not on "a controller must be bought".
8. **Hardware prices (M6 ₹99,900, Runpod rates) are REPORTED from the package; I could not re-fetch them** and the two research artifacts disagree with each other on Runpod rates (raw report: A5000 $0.27/h secure; package: $0.16/h community). Treat all prices as stale until refreshed at purchase time.

### A3. What remains uncertain (UNKNOWN)

- Runtime state of Mark-2 today (services active, errors, disk, Ollama models, timer status). Last evidence 2026-09-09.
- Whether `SCS.ADMIN01` (office PC, OpenClaw gateway logs 31 Aug) is the same machine as the "office Radeon 24GB PC". The package treats them as separate; the repo never names the Radeon machine.
- Exact Radeon SKU and OS.
- Whether the owner intends the repos to be public.
- Any SEVAACONNECT or Project X code. None exists in this repo. `work/leads/` holds six Upwork proposal drafts from 2026-09-13 (n8n/GoHighLevel/HubSpot automation gigs) — that is the only business-domain artifact in the repo.
- Real token spend to date: governor shows ₹0 strong-model spend in a fresh seed; live DB unknown.

### A4. Contradictions found (with resolution)

| # | Contradiction | Resolution |
|---|---|---|
| C1 | README: "Ubuntu PC is the permanent office / canonical brain" vs research: "migrate to Mac controller" vs Mark-2 audit: "Mark-2 cloud droplet is where AION runs" | **Resolved by ADR-02:** the controller is *wherever the hardened AION host is*; today that is Mark-2. No purchase until the Phase-1 exit gate. |
| C2 | Package: "Strategy Factory rule: never public" vs live: public | Owner decision OD-01. History scan of `lucyos-` is clean; `strategy-factory` history NOT scanned (out of scope) — task LQ-04. |
| C3 | Package `02_CURRENT_STATE`: backup "restore drill evidence not found" vs `DRIVE_BRIDGE_RESUME.md`: "restored with integrity OK (13 tasks, 18 memories)" | Both true: a same-disk temp-dir restore is exercised nightly; an **off-host, clean-machine restore has never been done**. |
| C4 | `agents.py` DEFAULT_AGENTS lists `openclaw` as "orchestrator" with `allowed_tools=fs,git,shell,http` vs research "OpenClaw must not be the kernel" | `allowed_tools` is inert metadata. In code, OpenClaw is only a transport (`whatsapp_bridge.py`). The registry naming is misleading; rename in LQ-07. |
| C5 | Package: "M4 is stale, compare M6" vs the actual question "should a Mac be bought at all" | Reframed in ADR-02. |
| C6 | Directives: "OpenClaw local shared state is the canonical source of truth" vs code: `AION_HOME/state/aion.sqlite3` is canonical | Same thing by two names (`~/openclaw/shared_brain`). Terminology cleanup only. |
| C7 | Raw report Runpod "Secure Cloud" rates vs package "community" rates | Not resolvable offline; both flagged stale. |

### A5. Evidence that materially changed my view

- Reading `worker.py` line-by-line: the execution boundary is bypassable with shell metacharacters. This moved "capability broker" from "important" to **the first engineering task after backups**.
- `mark2-desktop-commander.service`: moved "Mark-2 hardening" from Phase 2 to **Phase 0 owner action**.
- Discovering that the running controller is a 4 GB cloud VPS with 0.5B-parameter local models: changed the hardware recommendation from "buy a Mac" to "**buy nothing for 60–90 days; harden and measure**".
- The test suite passing cleanly with zero third-party dependencies: strongly supports KEEP for AION and makes portability (Linux VPS → Linux mini-PC → Mac) cheap.

---

## PART B — CURRENT REALITY

### B6. VERIFIED IMPLEMENTED (I read the code and/or ran it)

| Component | Where | Notes |
|---|---|---|
| SQLite canonical state, WAL, 13 tables incl. FTS on memory | `aion_core/db.py` | schema v5 |
| Task lifecycle with evidence-gated completion, claims, stale-claim release, retries→block, EV ranking | `tasks.py` | |
| Approval queue (`A-nnn`), strict `APPROVE <ID>` parsing, idempotent decisions | `approvals.py`, `router.py` | weak binding, see A2.5 |
| Deterministic command router (no model) | `router.py` | works offline |
| Model routing DET→A→B→C→D, one-step escalation | `agents.py` | routing is rule-based, auditable |
| Budget governor with 7 states, downshift-only | `governor.py`, `metrics.py` | ₹200/day, ₹2,000/month, ₹2,000 strong-model build cap defaults |
| Autonomous worker loop with flock singleton, prefix allowlist, dry-run, safe mode, pause | `worker.py` | boundary is weak (S-05) |
| Plan ingestion (JSON task graph from strong model) | `plan.py` | |
| Secret redaction/scan + pre-commit hook | `security.py`, `scripts/pre-commit` | |
| Same-disk backup with integrity-check restore | `backup.py` | |
| WhatsApp bridge (stdin/file/webhook/Meta Cloud API with HMAC signature + allowed sender) | `bridges/whatsapp_bridge.py` | Cloud adapter is sound |
| Phone web UI with bearer token, CSP, loopback bind, `/api/v1/*` JSON | `bridges/http_server.py`, `web/` | |
| Guarded Google Drive exchange bridge + tests with fake remote | `bridges/drive_bridge.py` | not live |
| systemd sandboxing on bridge/interface/drive units | `systemd/*.service` | good pattern; but runs as root |
| 205 unit/integration tests | `tests/` | pass in clean env |

### B7. PARTIAL

- Backups: same-disk only; no encryption; no off-host copy; `private_state` never backed up.
- Secret store is one flat env file (0600) whose whole content is exported into the bridge process environment.
- Approvals: exist, but no expiry, no scope binding, sender authority = channel token.
- Observability: `events` table + `health.run_all()`; no external alerting except owner channel.
- Local inference: Ollama present on Mark-2 (REPORTED) with tiny models.
- Phone UI: built; iPhone acceptance (TASK-607616E8) still NEEDS_REVIEW per handoff doc.

### B8. BROKEN / OBSOLETE / DUPLICATED

- **BROKEN-BY-DESIGN (security):** `mark2-desktop-commander.service` (root remote shell via npm relay).
- **BROKEN (blocked):** Drive bridge live path — Google Drive API disabled in the credential's Cloud project.
- **REPORTED BROKEN (2026-09-09):** maintenance service exited 1; work timer elapsed with no next run; six open command-failure errors. Current state UNKNOWN.
- **DUPLICATED:** nine directive prompt files + `docs/MASTER_AI_PROMPT.txt` + `fable.py` generated prompts all restate the same authority rules in prose. One versioned policy file should generate the rest (LQ-08).
- **OBSOLETE:** `TOMORROW.md` and `docs/MASTER_AI_HANDOFF.md` describe superseded next steps (still useful history).
- **MISLEADING:** `agents.py` registers `openclaw` as "orchestrator" with `shell` tools; nothing enforces or uses it.

### B9. UNKNOWN systems

SCS.ADMIN01 current state; Radeon PC identity; Project X; SEVAACONNECT automation; current live DB contents; whether anyone other than the owner has the interface/bridge tokens.

### B10. Existing assets worth preserving (KEEP list)

1. AION kernel + its test suite + zero-dependency stance.
2. Evidence-gated completion and the "boot names the bottleneck, never blindly reruns" resume semantics.
3. Governor downshift-only rule ("cost can only fall automatically").
4. systemd sandboxing pattern in the unit files.
5. WhatsApp Cloud API adapter (signature + sender allowlist).
6. Drive bridge's fail-closed content filters (reuse the pattern for every external content ingester).
7. Directive principle: "a blocked approval stops only that action".
8. Strategy Factory's evidence discipline (REPORTED; outside this repo).
