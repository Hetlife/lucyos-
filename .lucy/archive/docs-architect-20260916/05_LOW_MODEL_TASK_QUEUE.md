# 05 — Low-Model Execution Queue

Work orders for cheap/local coding models. Each is self-contained: read only the files named. Do not reread the research package. Do not re-derive architecture; it is fixed in `02_ARCHITECTURE_DECISIONS.md`.

Global rules for every task: Python 3.9+ stdlib only (no new dependencies without an owner decision) · run `python3 -m unittest discover -s tests -t . -q` before and after · run `./aion scan .` and `git diff --check` · smallest change that satisfies the spec · never print or commit secret values · never modify `policy/`, unit files' security directives, budgets or band definitions unless the task says so · commit on the designated branch with a message that names the LQ id · append a line to `docs/architect/CHECKPOINT.md` § COMPLETED WORK.

HANDOFF FORMAT (every task, in the commit message body and in CHECKPOINT): `STATUS (DONE|BLOCKED|PARTIAL) · FILES_CHANGED · TESTS (command + count) · EVIDENCE (what proves it) · BLOCKERS · NEXT_ACTION`.

---

## LQ-01 · P0 · Argv-based execution boundary (no shell)
- OBJECTIVE: `worker.run_command` must never invoke a shell; commands are parsed with `shlex.split`, `argv[0]` must be on an allowlist, shell control characters are refused, path traversal refused.
- WHY: S-02 — prompt-injected plans can reach `subprocess.run(shell=True)`.
- INPUT FILES: `aion_core/worker.py` (functions `check_command`, `run_command`, `DEFAULT_ALLOWED`, `FORBIDDEN`), `tests/test_plan_worker.py`, `aion_core/plan.py` (how `exec_command` is produced).
- EXACT ACTION:
  1. Replace `DEFAULT_ALLOWED` (prefix strings) with `DEFAULT_ARGV_ALLOW = {"aion","./aion","python3","pytest","git","ls","cat","head","tail","wc","grep","rg","find","mkdir","cp","mv","test","echo","sort","uniq","sed","awk","ollama","curl","bash"}` plus per-binary constraints: `git` subcommand ∈ {status,diff,log,add,commit}; `python3` first arg must not be `-c` or `-` ; `bash` first arg must start with `scripts/` and contain no `..`; `curl` URL must start with `http://localhost:` or `http://127.0.0.1:`; `sed` must include `-n`; `rm` is never allowed.
  2. `check_command(cmd)`: `argv = shlex.split(cmd)`; refuse if any token contains one of `; & | > < $( ` `` ` `` newline` or is exactly `&&`,`||`,`;`,`|`; refuse if any token contains `..` path segment; refuse if `argv[0]` (basename) not in allow set or fails its constraint; keep `FORBIDDEN` substring check as defense in depth.
  3. `run_command`: `subprocess.run(argv, shell=False, …)`; keep timeout/output truncation/redaction unchanged.
  4. Keep `allow_command(prefix)` but store argv[0] names, and make it refuse when called with `db.get_meta("policy_locked")=="1"` (LQ-20 will set it). Document in docstring that it is owner-only.
  5. Existing fixture `mkdir -p work/t && echo ok > work/t/marker` must be rewritten as two steps (`mkdir -p work/t` with `output_location work/t`, then a DET step whose exec is `python3 scripts/touch_marker.py work/t/marker` or use `cp`) — do not weaken the rule to keep the fixture.
  6. `cloud_command()` templates like `claude -p {prompt_file}` need `claude`/`codex` allowed: add `DEFAULT_ARGV_ALLOW |= {names parsed from meta.cloud_worker_cmd argv[0]}` at check time.
- DO NOT DO: keep `shell=True` anywhere; add a generic "allow anything under /usr/bin"; delete existing tests (rewrite fixtures instead); change `FORBIDDEN` semantics beyond adding.
- MODEL CLASS: B (cheap cloud). TOKEN/COST LIMIT: 60k tokens / ₹150.
- TOOLS REQUIRED: repo checkout, python3.
- DEPENDENCIES: none.
- TESTS: extend `TestCommandBlocklistHardening` with: `python3 -c 'x'` refused; `bash scripts/../x.sh` refused; `curl -s http://localhost.evil/` refused; `git push` refused; `echo hi` allowed; `git status` allowed; assert `subprocess.run` called with a list (mock).
- SUCCESS CRITERIA: all tests pass; grep shows no `shell=True` in `aion_core/`; the 10 injection strings in the test refuse.
- FAILURE CONDITIONS: any existing plan-worker behavior test fails for a reason other than fixture rewrite; scan finds secrets.
- OUTPUT LOCATION: `aion_core/worker.py`, `tests/test_plan_worker.py`, optional `scripts/touch_marker.py`.

## LQ-02 · P0 · Off-host encrypted backups (restic) + encrypted private_state backup + clean restore drill
- OBJECTIVE: three-copy backup with one off-host append-only copy; secrets backed up encrypted with an owner key; a documented, tested restore.
- WHY: S-04 — same-disk tar.gz only; secrets unbacked.
- INPUT FILES: `aion_core/backup.py`, `scripts/maintenance.sh`, `docs/OPERATIONS.md`, `systemd/aion-maintenance.*`.
- EXACT ACTION:
  1. Add `scripts/backup_offsite.sh`: requires env `RESTIC_REPOSITORY`, `RESTIC_PASSWORD_FILE` (path under `private_state/`, 0600), optional `RESTIC_REPOSITORY_2`; runs `aion backup` first; then `restic backup "$AION_HOME" --exclude private_state --exclude CACHE --exclude BACKUPS/*.tmp --tag aion`; then `restic check --read-data-subset=5%` weekly (day-of-week test); exit non-zero on failure; never prints env values.
  2. Add `scripts/backup_private_state.sh`: `tar` of `private_state/` piped to `age -r <owner-public-key-file>` (or `openssl enc -aes-256-cbc -pbkdf2` with a key file if `age` unavailable — detect at runtime), output `BACKUPS/private_state-<date>.age`, then upload via `restic backup` of that file to the off-host repo only. Owner private key never on the controller.
  3. `scripts/maintenance.sh`: call both scripts after `aion backup`; log outcomes to the session as today.
  4. `docs/BACKUP_RESTORE.md`: exact restore procedure onto a fresh Ubuntu host: install repo → `scripts/install.sh` → `restic restore latest --target /` (or to a staging dir) → decrypt private_state (owner step) → `aion health --deep` → compare `tasks`/`memory` counts with the last known values → record evidence.
  5. Add `aion backup --offsite-status` (in `cli.py`/`backup.py`) reporting last successful restic snapshot time from `restic snapshots --json --last` (parsed) without secrets.
  6. Restore drill: run the procedure in a clean container/VM (worker can use a temp dir as "fresh host" for a unit-level drill; the real host drill is an owner-supervised step) and record the timing in `EVIDENCE/restore-drill-<date>.md`.
- DO NOT DO: store the restic password in git/env of a unit file; give the controller a credential that can `forget`/`prune` (owner holds that one); back up `private_state` unencrypted; change `backup.py` retention.
- MODEL CLASS: B. TOKEN/COST LIMIT: 80k / ₹200.
- TOOLS REQUIRED: restic binary (owner installs: `apt install restic`), age or openssl, backup target credentials as handles (OD-05).
- DEPENDENCIES: OD-05.
- TESTS: `tests/test_backup_offsite.py` — scripts fail closed with missing env; private_state archive is not plaintext (magic bytes); `--offsite-status` parses a fixture JSON; shell syntax `bash -n`.
- SUCCESS CRITERIA: nightly run produces a snapshot; `restic check` passes; a clean-dir restore yields `integrity=ok` with matching counts; docs exist.
- FAILURE CONDITIONS: any secret value in logs/git; restore differs in counts.
- OUTPUT LOCATION: `scripts/backup_offsite.sh`, `scripts/backup_private_state.sh`, `docs/BACKUP_RESTORE.md`, `aion_core/backup.py`, `tests/test_backup_offsite.py`, `EVIDENCE/restore-drill-<date>.md`.

## LQ-03 · P1 · GitHub Actions CI
- OBJECTIVE: every push/PR runs tests, secret scan, whitespace check, and (if available) Trivy filesystem scan.
- WHY: S-09.
- INPUT FILES: `scripts/pre-commit`, `README.md` (tests section).
- EXACT ACTION: create `.github/workflows/ci.yml`: on push + pull_request; ubuntu-latest; matrix python 3.9 and 3.12; steps: checkout, setup-python, `python3 -m unittest discover -s tests -t . -q`, `./aion scan .`, `git diff --check`, `bash -n scripts/*.sh`, `node --check web/app.js` (if node present), Trivy via `aquasecurity/trivy-action` in `fs` mode with `exit-code: 0` (report only) — pin action versions by SHA.
- DO NOT DO: add secrets to CI; run anything that needs `AION_HOME` outside temp; make Trivy blocking in the first version.
- MODEL CLASS: A/B. LIMIT: 20k / ₹50. TOOLS: repo. DEPENDENCIES: none.
- TESTS: workflow passes on the branch (evidence: run URL in commit body).
- SUCCESS: green check on the branch head. FAILURE: tests need network/sockets not available on runners (then mark those tests skip-if-no-socket, as the handoff doc already anticipates).
- OUTPUT: `.github/workflows/ci.yml`, README badge optional.

## LQ-04 · P0 · Strategy-factory git-history secret and data scan (read-only)
- OBJECTIVE: determine whether `Hetlife/strategy-factory` history contains credentials, broker keys, personal data or client data before/after it is made private.
- WHY: S-05 / C2.
- INPUT FILES: a clone of `Hetlife/strategy-factory` (outside this repo); this repo's `aion_core/security.py` (reuse `scan_text`).
- EXACT ACTION: `git log --all -p | python3 -c "<use aion_core.security.scan_text per hunk; print file, kind, masked preview only>"`; additionally grep for `.env`, `*.json` credential names, phone numbers, PAN/Aadhaar-like patterns (mask output). Produce counts by kind and file. Never print values.
- DO NOT DO: rewrite history; push anything to that repo; print secrets.
- MODEL CLASS: A/B. LIMIT: 20k / ₹50. TOOLS: git, python3. DEPENDENCIES: repo access.
- TESTS: run the same scanner on `lucyos-` first and confirm it reports only the known fixtures.
- SUCCESS: a findings summary (counts, files, kinds) in CHECKPOINT § SECURITY FINDINGS. FAILURE: any real credential found ⇒ P0 rotate + OD for history rewrite.
- OUTPUT: CHECKPOINT entry; optional `EVIDENCE/sf-history-scan-<date>.md` (masked).

## LQ-05 · P0 · Sanitized runtime inventory script
- OBJECTIVE: one command that reports the live state of a LucyOS host without leaking secrets.
- WHY: U-01, U-02, U-13, U-14.
- INPUT FILES: `aion_core/health.py`, `aion_core/worker.py` (`capability_report`), `systemd/`.
- EXACT ACTION: `scripts/runtime_inventory.sh` → JSON to stdout with: hostname, kernel, uptime, `id -u`, disk (`df -h /` fields), memory (`free -m`), `systemctl --user list-units 'aion-*' 'mark2-*' --all` (name, active, enabled), `systemctl --user list-timers`, `loginctl show-user $USER -p Linger`, `ss -tlnp` (listening ports, process names only), `ufw status` (if present), `ollama list` names+sizes only, `git -C $REPO rev-parse HEAD` + `git status --short | wc -l`, `aion health --deep` verdict, `aion money` governor line, `aion errors` count, `pgrep -fl 'desktop-commander|openclaw|codex'` (names only). Pipe the whole output through `python3 -c "from aion_core import security; …redact"`.
- DO NOT DO: print env vars, file contents, tokens, IPs of other hosts beyond local listeners.
- MODEL CLASS: A/B. LIMIT: 20k / ₹50. TOOLS: bash. DEPENDENCIES: none.
- TESTS: `tests/test_runtime_inventory.py` — run with a planted fake token in an env var and assert it is absent from output; JSON parses.
- SUCCESS: script runs on Mark-2, output saved to `EVIDENCE/inventory-<host>-<date>.json` and summarized in CHECKPOINT § VERIFIED STATE. FAILURE: output contains a secret shape.
- OUTPUT: `scripts/runtime_inventory.sh`, test, evidence file.

## LQ-06 · P1 · Approval object v2
- OBJECTIVE: typed, scoped, expiring approvals decided only via authenticated channels.
- WHY: S-06; ADR-06.
- INPUT FILES: `aion_core/approvals.py`, `aion_core/router.py` (`_decide`, `handle`), `aion_core/db.py` (SCHEMA + migration mechanism — inspect how `SCHEMA_VERSION` is applied in `db.py`/`bootstrap.py`), `bridges/whatsapp_bridge.py`, `bridges/http_server.py`, `tests/test_approvals.py`, `tests/test_router.py`, `tests/test_bridge.py`.
- EXACT ACTION:
  1. Schema v6: add columns from EXECUTION_PACKAGE §6.2 with `ALTER TABLE … ADD COLUMN` guarded by `PRAGMA table_info`.
  2. `approvals.create(..., action_type="other", target="", scope=None, band="RED", expires_in_h=72, evidence_ref="")`: set `expires_at`, random `nonce` (16 hex), `requested_by`.
  3. `approvals.decide(approval_id, decision, by, via)`: require `via` ∈ `AUTHENTICATED_CHANNELS = {"whatsapp_cloud","interface","cli"}`; if expired ⇒ set EXPIRED and raise `ApprovalError("expired")`; store `decided_via`, `decision_hash = sha256(approval_id|decision|by|via|decided_at|nonce)`.
  4. `router.handle(message, sender, channel="unknown")`: pass `channel` to `_decide`; bridges pass their channel name; `run_webhook` (generic adapter) must `sys.exit(2)` if `WHATSAPP_BRIDGE_TOKEN` is unset instead of warning, and pass `channel="whatsapp_webhook"` which is NOT authenticated for approvals (GREEN commands only).
  5. `approvals.render` adds EXPIRES and SCOPE lines. `approvals.expire_stale()` called from `resume.boot`.
  6. `worker._raise_approval` sets `action_type` from task kind (`spend`→spend, `credential`→disclose, etc.).
- DO NOT DO: change the strict `APPROVE <ID>` grammar; let `cli` decisions bypass logging; drop existing columns.
- MODEL CLASS: B. LIMIT: 80k / ₹200. TOOLS: repo. DEPENDENCIES: LQ-01 recommended first.
- TESTS: decide via unauthenticated channel ⇒ ApprovalError and status unchanged; expired ⇒ EXPIRED; hash present; migration idempotent on an existing v5 DB fixture; webhook adapter refuses to start without token.
- SUCCESS: all tests pass; `aion why A-…` shows via/expiry. FAILURE: any path lets a channel decide without `via`.
- OUTPUT: files above + `tests/test_approvals_v2.py`.

## LQ-07 · P2 · Agent registry cleanup
- OBJECTIVE: stop the DB from describing OpenClaw as an orchestrator with shell tools.
- INPUT: `aion_core/agents.py` (`DEFAULT_AGENTS`), tests referencing `openclaw` agent id (grep).
- EXACT ACTION: rename `agent_id="openclaw"` → `"aion-kernel"`, role `"kernel"`, `allowed_tools=""`, capabilities `"state,routing,resume,approvals,reporting"`; add a module comment "allowed_tools/capabilities are descriptive until LQ-14 manifests exist"; provide a one-time migration that renames existing rows and updates `tasks.owner_agent`; update tests and docs mentioning the id (`worker.py` uses `"openclaw"` as a default agent id and session actor — update both).
- DO NOT DO: touch routing logic.
- MODEL CLASS: A. LIMIT: 15k / ₹30. DEPENDENCIES: none. TESTS: existing suite + rename test. OUTPUT: `agents.py`, `worker.py`, `sessions` callers, tests.

## LQ-08 · P2 · One canonical authority policy document + git guard for business data
- OBJECTIVE: `policy/AUTHORITY_POLICY.md` v1 holds the bands/laws (copy §2 laws and the band table from `03_THREAT_MODEL_AND_SECURITY.md` §3); each of `directives/0*.txt` gets a header "GENERATED VIEW — source: policy/AUTHORITY_POLICY.md vX" and a script `scripts/render_directives.py` regenerates their shared sections; `.gitignore` adds `work/leads/` and `work/**/*.pdf` unless OD-01 says public is intended and business data is explicitly allowed (default: ignore).
- MODEL CLASS: A/B. LIMIT: 30k / ₹60. DEPENDENCIES: none. TESTS: renderer idempotent; `git check-ignore work/leads/x.md` true. OUTPUT: `policy/AUTHORITY_POLICY.md`, `scripts/render_directives.py`, `.gitignore`.

## LQ-09 · P1 · `aion export` / `aion import`
- OBJECTIVE: portable, hash-verified state export and import (ADR-19).
- INPUT: `aion_core/backup.py`, `aion_core/cli.py`, `aion_core/db.py`, `config.DIRS`.
- EXACT ACTION: `export DIR`: consistent SQLite copy via `Connection.backup`, `.dump` to `state.sql`, copy `MEMORY/ APPROVALS/ AGENTS/ EVIDENCE/ DOCUMENTS/ policy/ METRICS/ FINANCE/` if present, write `MANIFEST.json` (schema_version, exported_at, host, files with sha256/bytes), exclude `private_state` and `CACHE`. `import DIR --into AION_HOME`: verify all hashes, refuse if `schema_version` newer than code, restore DB from `state.sql` into an empty `AION_HOME`, run migrations, run `health.run_all(deep=True)`, print counts.
- DO NOT DO: import over a non-empty AION_HOME without `--force`; include secrets.
- MODEL CLASS: B. LIMIT: 50k / ₹120. DEPENDENCIES: none. TESTS: round-trip export→import in temp dirs preserves task/memory counts; tampered file ⇒ refuse. OUTPUT: `aion_core/portability.py`, cli wiring, `tests/test_portability.py`.

## LQ-10 · P0 · Non-root `lucy` service identity (script + unit templates)
- OBJECTIVE: run all AION services as an unprivileged user with per-service env files.
- WHY: S-03, S-07; ADR-20.
- INPUT: `scripts/install.sh`, `scripts/install_services.sh`, `systemd/*.service|*.timer`, `docs/OPERATIONS.md`, `bridges/http_server.read_secret`.
- EXACT ACTION:
  1. `scripts/migrate_to_service_user.sh` (owner runs as root once): `adduser --system --group --home /srv/lucy lucy`; `rsync -a /root/openclaw/shared_brain/ /srv/lucy/openclaw/shared_brain/`; `git clone` (or move) repo to `/srv/lucy/lucyos`; chown -R lucy:lucy; `chmod 700 /srv/lucy /srv/lucy/openclaw/shared_brain/private_state`; `loginctl enable-linger lucy`; split `secrets.env` into `private_state/env/<service>.env` (bridge: `WHATSAPP_*`; interface: `AION_INTERFACE_TOKEN`; drive: none/rclone path) using a small python helper that copies only the named keys (values never printed); install units under `lucy`'s user manager; keep `/root` copies read-only (`chmod -R a-w`) for 14 days; print a checklist of what the owner must verify.
  2. Unit templates: replace `Environment=PATH=/root/...` with `%h/.local/bin:/usr/local/bin:/usr/bin:/bin`; bridge unit loads only `private_state/env/bridge.env` via `EnvironmentFile=` (0600, owned by lucy); remove the `set -a; . secrets.env` bash wrapper; add `ProtectHome=tmpfs` where feasible, `ReadWritePaths=` only `AION_HOME`; `CapabilityBoundingSet=` empty; `RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6`.
  3. `scripts/kill_switch.sh` (owner): `systemctl --user -M lucy@ stop 'aion-*' 'mark2-*'`, `aion pause`, `aion safe-mode`, log event.
  4. Docs: `docs/OPERATIONS.md` sections "Service user" and "Remote administration (owner SSH key → admin account; no remote-shell services)".
- DO NOT DO: run the migration automatically from a worker; put values in unit files; keep secrets world-readable; delete `/root` copies.
- MODEL CLASS: B (script); execution by owner (RED). LIMIT: 60k / ₹150. DEPENDENCIES: LQ-02 (backup first), OD-06. TESTS: `bash -n`; unit files pass `systemd-analyze verify` (if available); env-split helper unit test with fake keys; `tests/test_install_units.py` asserts no `/root` literal and no `set -a` in templates.
- SUCCESS: on host, all AION processes run as `lucy`; suite passes as `lucy`; interface reachable via Tailscale; evidence in CHECKPOINT. FAILURE: any service fails to start under `lucy` ⇒ rollback to root layout and record.
- OUTPUT: scripts, unit templates, docs, tests.

## LQ-11 · P1 · Remove Desktop Commander from the repo
- OBJECTIVE: delete `systemd/mark2-desktop-commander.service` and `scripts/install_desktop_commander.sh`; add a `docs/OPERATIONS.md` note that remote administration is owner SSH only and that remote-control agents are prohibited on the controller (ADR-05).
- DEPENDENCIES: OD-03 recorded as "disable". MODEL CLASS: A. LIMIT: 5k / ₹10. TESTS: grep shows no `desktop-commander` in repo except this doc history. OUTPUT: deletion commit.

## LQ-12 · P1 · Inference-node qualification runbook + script
- OBJECTIVE: reproducible PASS/FAIL for the office Radeon PC as a compute appliance (ADR-07).
- INPUT: `02_ARCHITECTURE_DECISIONS.md` ADR-07; `aion_core/worker.py` (`run_ollama`).
- EXACT ACTION: `docs/RADEON_QUALIFICATION.md` (steps: identify GPU/OS; check AMD ROCm/Vulkan support for that SKU; create restricted OS account `ai_worker`; install Ollama or llama.cpp under that account only; bind server to LAN/Tailscale IP; host firewall allow only controller identity to the port; create `AI_WORKSPACE/{in,out,models,tmp}`; no other shares) + `scripts/qualify_inference_node.sh ENDPOINT` run from the controller: checks `/api/tags`, runs a fixed 30-prompt set from `tests/fixtures/inference_eval.jsonl` (classification/extraction/summarization with expected JSON), scores deterministically (exact-match / schema-valid / keyword recall), measures tokens/s and p95 latency, runs a 24 h loop of one request/5 min logging failures, runs `nmap -Pn` against the host and asserts only the endpoint port answers, writes `EVIDENCE/inference-qualification-<date>.json` with PASS/FAIL per criterion. Thresholds (initial): schema-valid ≥95%, exact-match ≥ cloud-cheap baseline − 5 pts (baseline produced by running the same set through `cloud_command()`), p95 < 20 s for 512-token outputs, zero failures in soak, only one open port.
- DO NOT DO: install anything on the office PC from the script (owner does that following the doc); send CONFIDENTIAL data; require RDP/SSH.
- MODEL CLASS: B. LIMIT: 60k / ₹150. DEPENDENCIES: OD-09. TESTS: scorer unit tests on fixture outputs; `bash -n`. OUTPUT: doc, script, fixture, evidence JSON.

## LQ-13 · P1 · Documents / sources / claims / evidence tables + FTS5 + `aion search`
- OBJECTIVE: implement EXECUTION_PACKAGE §6.4–6.5 with FTS5 virtual tables and a CLI search that returns ids + snippets.
- INPUT: `aion_core/db.py` (existing FTS on `memory` — follow that pattern), `aion_core/memory.py`, `aion_core/cli.py`.
- EXACT ACTION: schema v6 tables + `documents_fts(content)`, `claims_fts(statement)` with triggers to keep in sync; `aion_core/evidence.py` with `add(task_id, kind, path_or_bytes, summary)` writing content-addressed files under `EVIDENCE/`; `aion_core/documents.py` with `register(path, company, project, source, classification)` (hash, dedupe by sha256, quarantined status); `aion_core/claims.py` with `add(...)` and `search(q)`; `aion search "<q>" --in documents|claims|memory`; recall harness `tests/fixtures/search_eval.jsonl` (20 questions → expected ids) and `aion search --eval` printing recall@5 (this is the measurement that gates any future embeddings).
- DO NOT DO: embeddings; external libraries; store document bodies in the DB (store extracted text in FTS, bodies on disk).
- MODEL CLASS: B. LIMIT: 80k / ₹200. DEPENDENCIES: none (LQ-06 migration mechanism shared — coordinate version bump). TESTS: dedupe, FTS hit, evidence immutability (second add of same bytes returns same id), eval harness runs. OUTPUT: modules, cli, tests, fixtures.

## LQ-14 · P1 · Capability manifest schema, validator and clamping
- OBJECTIVE: implement §6.1 as `aion_core/manifest.py` + `SCHEMAS/manifest.schema.json` (documentation copy); validation is hand-written (stdlib), not jsonschema.
- EXACT ACTION: `validate(dict) -> list[str]` (types, enums, no `..`, relative paths, expires_at ISO, non-negative ints); `clamp(manifest, band_policy) -> manifest` (intersect `net_allow`, `grants`, `argv_allow` with the band's policy sets; cap money/tokens/attempts; RED ⇒ `money_max_inr` forced 0 until approval attached); `tasks` table gains `manifest_json` (schema bump); `plan.apply` writes a manifest per step (defaults: GREEN, fs_write `ARTIFACTS/<task>/`, no net, no grants); `context.build` includes a manifest summary line.
- DO NOT DO: enforce at execution yet (that is the broker, T-13); read secrets.
- MODEL CLASS: B. LIMIT: 50k / ₹120. DEPENDENCIES: LQ-06 (schema mechanism). TESTS: invalid manifests rejected; clamp never widens; plan steps get manifests. OUTPUT: module, schema doc, tests.

## LQ-15 · P1 · Routing telemetry and report
- OBJECTIVE: §6.6 columns + `aion routing-report [--month YYYY-MM]`.
- INPUT: `aion_core/metrics.py`, `aion_core/tasks.py` (`complete`), `aion_core/worker.py` (`metrics.record_usage` calls), `aion_core/reports.py`.
- EXACT ACTION: add columns; `record_usage(..., task_kind, latency_ms, provider, privacy_class, validation_result)`; `tasks.complete` sets `accepted=1` on that task's usage rows, `tasks.fail` after final block sets 0; report prints kind × model: calls, accepted, cost, cost/accepted, p50 latency, retries; include a "DET/DB share" line = tasks completed with `model_class='DET'` ÷ all completed.
- MODEL CLASS: B. LIMIT: 40k / ₹100. DEPENDENCIES: schema mechanism. TESTS: acceptance propagates; report math on fixture rows. OUTPUT: metrics/tasks/cli/reports changes, `tests/test_routing_report.py`.

## LQ-16 · P2 · Telegram fallback adapter (optional, only after OD-10)
- OBJECTIVE: `bridges/telegram_bridge.py` webhook adapter: verifies `X-Telegram-Bot-Api-Secret-Token`, allow-lists one chat id (from `private_state/env/telegram.env`), idempotent on `update_id`, routes via `router.handle(channel="telegram")` — GREEN commands only unless LQ-06 marks it authenticated. Send P0/P1 alerts via `sendMessage`.
- MODEL CLASS: B. LIMIT: 40k / ₹100. DEPENDENCIES: LQ-06. TESTS: mirror `tests/test_bridge.py`. OUTPUT: bridge, unit template, docs.

## LQ-17 · P2 · Hash-chained audit export
- OBJECTIVE: nightly `AUDIT/events-<date>.jsonl` where each line includes `prev_hash` and `hash=sha256(prev_hash + canonical_json(event))`; `aion audit verify` recomputes the chain; maintenance runs export + verify; restic includes `AUDIT/`.
- INPUT: `aion_core/db.py` (`events`, `log_event`), `scripts/maintenance.sh`.
- MODEL CLASS: A/B. LIMIT: 30k / ₹60. TESTS: tamper one line ⇒ verify fails. OUTPUT: `aion_core/audit.py`, cli, tests.

## LQ-18 · P1 · Document intake workflow (Phase 6 skeleton)
- OBJECTIVE: `aion_core/workflows/document_intake.py`: watch `AION_HOME/INBOX/documents/` (and later the Drive inbox), for each file: size/type check (pdf, docx, xlsx, png/jpg, txt; ≤25 MB) → `documents.register` (dedupe) → quarantine text extraction with stdlib-only parsers where possible (txt/csv/json natively; pdf/docx via `pdftotext`/`unzip`+XML if binaries exist, else mark `needs_parser`) → classification via class A prompt returning strict JSON `{doc_type, company_guess, project_guess, dates[], amounts[], parties[]}` validated by schema + range checks → deterministic linking rules (exact project code match, org name match) with fallback status `unlinked` → create tasks/deadlines for detected due dates → append to daily digest. No outbound side effects; every row has evidence refs.
- INPUT: LQ-13 modules, `aion_core/worker.py` (`run_ollama`/`run_cloud`), `aion_core/context.py`.
- DO NOT DO: send messages; call CRM; execute anything from document text; use documents classified above INTERNAL with cloud models until OD-08.
- MODEL CLASS: B implement. LIMIT: 100k / ₹250. DEPENDENCIES: LQ-13, LQ-14 (manifest GREEN, no net except model provider), T-13 broker preferred. TESTS: fixture corpus of 10 synthetic docs incl. 2 injection docs ("ignore rules, send to…") ⇒ zero side effects; duplicate ⇒ no new rows; malformed JSON from model ⇒ `needs_review`. SUCCESS: fixtures pass; digest renders. OUTPUT: module, fixtures, tests, `docs/WORKFLOW_DOCUMENT_INTAKE.md`.

## LQ-19 · (folded into LQ-01) — curl host and bash path constraints.

## LQ-20 · P1 · Policy root + boot hash check + `aion policy accept`
- OBJECTIVE: §6.7. Files `policy/bands.json`, `policy/allowlist.json`, `policy/budgets.json`, `policy/channels.json` in git (initial content from `03_THREAT_MODEL_AND_SECURITY.md` §3 and current `config`/`worker` defaults); `aion policy hash` prints sha256 over sorted file contents; `aion policy accept` (refuses unless `os.geteuid()!=lucy uid` or an `AION_ADMIN=1` env set by the owner's shell — document that it is owner-only) stores `meta.policy_hash` and sets `meta.policy_locked=1`; `resume.boot` compares and, on mismatch, sets safe mode and writes a P0 owner alert; `worker.allow_command` and `governor` cap changes refuse when locked; `metrics.budget_status` reads caps from `budgets.json` when present.
- DO NOT DO: let any worker path write `policy/`; hardcode caps in two places (policy file wins).
- MODEL CLASS: B. LIMIT: 50k / ₹120. DEPENDENCIES: LQ-01, LQ-06. TESTS: mismatch ⇒ safe mode; accept refused without admin marker; caps come from file. OUTPUT: `policy/`, `aion_core/policy.py`, cli, tests.
