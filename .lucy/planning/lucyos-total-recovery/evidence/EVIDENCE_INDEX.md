# Evidence index (do not re-derive; cite by key)

| Key | Fact | Source / how verified | Date |
|---|---|---|---|
| EV-MAIN | `origin/main` = `36c954c`, 202 first-parent commits since history reset on 2026-09-13; remote HEAD is `main` | `git log`, `git ls-remote --symref origin HEAD` | 2026-09-30 |
| EV-TESTS | 795 tests OK, 2 skipped (sqlite-vec optional, ssh-keygen), 138 s, Python 3.11 | local run, `python3 -m unittest discover -s tests -t . -q` | 2026-09-30 |
| EV-CI | Run #376 on `36c954c`: all 8 jobs success incl. `macos-readiness` | GitHub Actions run 36696760240 | 2026-09-30 |
| EV-CI-CANCEL | 9 of the 13 CI runs for main SHAs between #75 and #87 ended `cancelled` (concurrency group cancels in-progress on push) | Actions list, branch=main | 2026-09-30 |
| EV-GATES | `check_portability` 0 violations/3 known; `aion scan .` clean; `anti-dup` ok; `check_boundaries` 2 warnings (`tasks.py`, `runtime_inventory.py` sqlite import) | local run, `evidence/gates_20260930.txt` | 2026-09-30 |
| EV-DRIFT | `verify_authority.py self`: 5 hash drifts (`lucyos-ci.yml`, `config.py`, `db.py`, `router.py`, `security.py`); freeze SHA `2a70020` | local run | 2026-09-30 |
| EV-SIZE | 27.6k Python lines; `aion_core` 12.2k in 57 files; 76 test files; 31 SQLite tables; schema v12; ~80 CLI subcommands | `wc`, `grep CREATE TABLE`, `cli.py` | 2026-09-30 |
| EV-BRANCHES | 127 remote branches: 54 CONTAINED, 7 PATCH_IN_BASE, 8 UNRELATED (no merge base), 58 UNIQUE | `scripts/branch_ledger.py` -> `branch_ledger_20260930.tsv` | 2026-09-30 |
| EV-PRS | 88 PRs: 63 merged, 18 closed, 7 open (#2, #11, #53, #62, #73, #88 + none draft-merged) | GitHub `list_pull_requests` | 2026-09-30 |
| EV-PR73 | #73 merged onto `36c954c`: 808 tests OK, anti-dup ok, `strict` fails only "worker.py protected; FABLE-10 has no override" | local worktree run | 2026-09-30 |
| EV-PR73-CI | #73's own CI (on 2026-09-25 head): code-and-test x3 failed + authority-gate failed — stale head, superseded by EV-PR73 | GitHub check runs | 2026-09-25 |
| EV-RUNNABILITY | Clean clone install, 9 seeded tasks, backup+restore-test, `aion status/tasks/boot/fable-ready/owner-setup`, stdin bridge all work | `docs/internal/LUCYOS_RUNNABILITY_AUDIT_20260930.md` (independent audit at `5d1c6e5`) | 2026-09-30 |
| EV-LIVE-DEN | Lucy-den: `aion openclaw-check` reported `reachable` (R-05); Nebula LucyNest native client live at 192.168.31.122, touch hardware faulty | `.lucy/execution/repair-20260923/PROGRESS.md`; branch `task/lucynest-source-reconciliation-20260925:docs/lucynest-resume-20260926.md` | 2026-09-24/26, **secondhand** |
| EV-LIVE-M2 | Mark-2: R-02 DET task proof ran on Mark-2 runtime; user-systemd detection fixed (#55); DC-1 SHA never named in deployment contract | PROGRESS.md; `.lucy/deployment/MARK2_DEPLOYMENT_CONTRACT.md` | 2026-09-24, **secondhand** |
| EV-DRIVE | Drive: `MARK2_SHARED` last modified 2026-09-09; `LUCYOS_BACKUP` folder created 2026-09-23; planning/handoff folders from 09-16/17; no evidence of an automated backup upload | Drive search (owner scs.admin01) | 2026-09-30 |
| EV-PHONE | Direct Meta bridge has never delivered to a real phone; needs 6 vars + public HTTPS tunnel; OpenClaw declared primary WhatsApp channel (R-06) | audit G-3, PR #79 | 2026-09-30 |
| EV-OPENCLAW-PATH | OpenClaw -> LucyOS path = `integrations/openclaw/lucyos` skill -> `lucyosctl` (local or forced-command SSH) -> read commands + `work --dry-run`. No governed write/approve verb exists on that path | `lucyosctl`, `lucyos-remote-dispatch` | 2026-09-30 |
| EV-PROJECT | "project" is a free-text column (default `'default'`) on tasks/finance/deliveries/memory/intake; no project or company entity; `api.projects()` derives names from distinct values; repo `PROJECTS/sevaa-sales-os/money_path.json` is the only project definition | `db.py`, `api.py` | 2026-09-30 |
| EV-SKILLS | Skill manifest schema + catalog + lifecycle + LearnRepo review gate exist (`skills/manifest.schema.json`, `aion_core/skills.py`, `learnrepo.py`); catalog INDEX has 0 entries | files | 2026-09-30 |
| EV-SCG | Secure Capability Gateway implemented on `integration/lucyos-autonomous-wave-20260919` (`aion_core/gateway.py`, COSE_Sign1, needs `scitt-cose`, `cbor2`, `cryptography`; edits CI); design-only RPAB doc; not merged | branch diff | 2026-09-20 |
| EV-MAC | Host adapter `aion_core/host/macos.py`, launchd plists, `install_services.sh` darwin branch, macOS CI green; `aion-work` plist runs once at load (no periodic re-run); never executed on a real Mac | files, CI | 2026-09-30 |
| EV-SECRETS | Single 0600 `private_state/secrets.env`; `aion secrets set/list`; excluded from backups/export; no scoping by project | `config.py`, `cli.py` | 2026-09-30 |
| EV-EXEC | Worker executes: DET via allowlisted argv (no shell); A via Ollama; B via free auxiliary gateway or one configured cloud command (`aion set-cloud-cmd '... {prompt_file}'`); C held for strong session; D raises approval; budget governor demotes | `worker.py`, `agents.py`, `governor.py` | 2026-09-30 |
| EV-DANGLING | `docs/internal/AGENT_START_HERE_20260930.md` cites `docs/internal/CODE_REVIEW_20260924.md`, which exists only on `review/code-review-20260924` | `ls`, branch | 2026-09-30 |
| EV-MAIN2 | `origin/main` = `fad9ed4` (#73, #88 merged); 3 branches deleted upstream (#73's, #88's, `test/authority-gate-positive`) | `git fetch --prune` | 2026-09-30 (pass 2) |
| EV-TESTS2 | 810 tests OK, 2 skipped, 148 s on `fad9ed4` merged into the planning branch; all gates as before | local run | 2026-09-30 (pass 2) |
| EV-DRIFT2 | `verify_authority.py self`: 6 drifts (adds `aion_core/worker.py`) | local run | 2026-09-30 (pass 2) |
| EV-CI-CANCEL2 | run #382 (`09fad0a`, #73 merge) cancelled by the #88 push; run #383 (`fad9ed4`) success | Actions | 2026-09-30 |
| EV-COMPILER | `context_compiler.compile_context` on the repo with a seeded home: BUILT 76 ms, 27 sources, 12 KB md / 17 KB json; CACHE_HIT 43 ms; called for every class before RUNNING | measured | 2026-09-30 |
| EV-DEAD-MODULES | `guardian`, `tempworker`, `intake`, `sync_outbox`: no importer outside tests | grep | 2026-09-30 |
| EV-UI | Control Center candidates: `web/` (629 lines vanilla, token auth, SSE, offline queue) + `api.py` 9 read models + `http_server.py`; PR #53 and the Drive `LUCYOS_UI_UX_MASTER_REFERENCE` (2026-09-17) both say extend this, no new stack; Framer: no repo artefacts | files, PR #53, Drive doc | 2026-09-30 |
| EV-LEDGER2 | 127 branches: 54 CONTAINED, 7 PATCH_IN_BASE, 7 UNRELATED, 59 UNIQUE (incl. 3 Fable branches) | `branch_ledger_20260930b.tsv` | 2026-09-30 |
| EV-BRANCH-DELETE | `git push --delete` from the agent session fails ("remote end hung up"); remote branch deletion is owner-only | attempted | 2026-09-30 |
