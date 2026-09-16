# LucyOS Architect Session — CHECKPOINT / PROGRESS

Last updated: 2026-09-16 (session 4: smallest-fix skill written, tested, pushed)
Branch: `claude/lucyos-architecture-audit-4o4q83` (pushed)
Status: ARCHITECTURE + EXECUTION PACKAGE COMPLETE. LQ-01 (argv execution boundary) DONE. learnrepo skill prepared (awaiting merge approval). smallest-fix skill built and pushed per explicit owner instruction. Remaining Phase 0/1 tasks open.

> RESUME RULE: a new AI must NOT reread the research ZIP. Read this file, then
> `LUCYOS_ARCHITECT_EXECUTION_PACKAGE.md`, then take the next task from
> "EXACT NEXT ACTION". Everything load-bearing from the research is reproduced
> with evidence classes in `01_CURRENT_STATE_AUDIT.md`.

## 1. CURRENT OBJECTIVE

Session 1 objective (DONE): independently audit the research package, produce decision-grade architecture, threat model, execution package, low-model task queue, owner decisions, and leave it all in the repo.
Next objective: execute Phase 0 (close P0 exposures, resolve UNKNOWNs) per the execution package §8, then Phase 1.

## 2. VERIFIED STATE

- [VERIFIED] Package and prompt uploads were byte-identical duplicates; package fully read (23 docs, QA, manifest, raw deep-research report, Mark-2 readiness audit text, deep-research master prompt).
- [VERIFIED] Repo `Hetlife/lucyos-` at `33e4ced` + this branch: 212 tests pass (Python 3.11.15, clean Linux container, 2026-09-16). Stdlib only. `./aion scan .` clean.
- [VERIFIED] Full git-history secret scan of `lucyos-`: only the documented test fixtures (the fake GitHub token and the AWS documentation example key in `tests/test_security.py`). No real credentials.
- [VERIFIED LIVE, GitHub API 2026-09-16] `Hetlife/lucyos-` public; `Hetlife/strategy-factory` public; also public: `Hetlife/paperclip` (fork), `Hetlife/claude-test`. Zero open issues on `lucyos-`.
- [VERIFIED by code] execution boundary is now argv-based (LQ-01 done: `shlex.split` + argv[0] allowlist + per-binary constraints + `subprocess.run(shell=False)`; no `shell=True` anywhere in the repo). Still open: `agents.allowed_tools` never enforced; approvals decided by any `sender` string; backups same-disk unencrypted, `private_state` never backed up; bridge exports entire secret file to env; root remote-shell unit `mark2-desktop-commander.service` shipped in repo.
- [REPORTED, 2026-09-09] Mark-2 = DigitalOcean droplet Ubuntu 24.04 2vCPU/4GB, AION runs as root, Ollama with qwen2.5-coder 0.5b/1.5b, Drive bridge blocked on Google Drive API disabled, maintenance service had exited 1, six open errors.
- [UNKNOWN] Mark-2 state today; SCS.ADMIN01 state; Radeon PC identity; Project X / SEVAACONNECT code (none in this repo).

## 3. CRITICAL FINDINGS (full list: 03_THREAT_MODEL_AND_SECURITY.md §1)

- S-01 P0 root remote-shell service on the controller (desktop-commander) → OD-03.
- S-02 P0 shell-injectable execution boundary → DONE (LQ-01, this session): argv-based, no `shell=True` left in the repo.
- S-03 P0 everything runs as root → LQ-10 / OD-06.
- S-04 P0 no off-host/encrypted backup; secrets unbacked → LQ-02 / OD-05.
- S-05 P0 repos public → OD-01 / LQ-04.
- S-06 P1 approval authority = channel token, no expiry/scope → LQ-06.
- A2 (audit): research under-weighted that the controller already exists (VPS), missed desktop-commander, overrated tiny local models, and asked "which Mac" instead of "buy at all".

## 4. FILES / REPOSITORIES INSPECTED

Package: all docs + evidence snapshots. Repo: README, docs/*, TOMORROW.md, aion_core/{security,approvals,governor,agents,config,backup,db(schema),worker,router,plan(head),fable(head),metrics(budget)}.py, bridges/{whatsapp_bridge,http_server,drive_bridge(head)}.py, systemd/*, scripts/*, directives/{00,02(grep),07}, deploy/queues (head), tests (executed). GitHub API: repo metadata, issues, user.

## 5. ARCHITECTURE DECISIONS — see 02_ARCHITECTURE_DECISIONS.md (ADR-01…20)

Headline: KEEP AION; controller = hardened Linux host (Mark-2 now, buy nothing until Phase-1 gate; Linux mini-PC default if on-prem later, Mac only by preference); SQLite+FTS5; no Temporal/n8n/K8s/vector DB; OpenClaw adapter-only; capability broker + GREEN/AMBER/RED + approvals v2 first; Radeon = appliance after gate; class A = cheapest *validated* executor (not "local"); WhatsApp Cloud API stays primary channel; first workflow = document intake; Strategy Factory evidence-only; portability via export/import; non-root service identity.

## 6. ASSUMPTIONS / UNKNOWNS — see 07_UNRESOLVED_QUESTIONS.md (U-01…14)

Prices (M6, mini-PC, Runpod, DO) are stale/REPORTED; refresh at purchase time. Mark-2 list price assumed ~$24/mo.

## 7. REJECTED ALTERNATIVES — see EXECUTION_PACKAGE §12 (binding list).

## 8. SECURITY FINDINGS — see 03_THREAT_MODEL_AND_SECURITY.md (S-01…13, hardening H-1…12).

## 9. CURRENT TASK

None in progress. Session 1 closed cleanly.

## 10. COMPLETED WORK

Session 1:
- Read + verified package; ran tests (205→207 OK); history secret scan; live visibility check.
- Committed: `docs/architect/{README,CHECKPOINT,01_CURRENT_STATE_AUDIT,02_ARCHITECTURE_DECISIONS,03_THREAT_MODEL_AND_SECURITY,05_LOW_MODEL_TASK_QUEUE,06_OWNER_DECISIONS,07_UNRESOLVED_QUESTIONS,LUCYOS_ARCHITECT_EXECUTION_PACKAGE}.md`.
- P0 partial fix: `worker.FORBIDDEN` hardened (`;`, `$(`, backtick, `|bash`, home wipes, sudo/ssh/wget/systemctl…) + 2 tests (commit 3126ff1).

Session 2 — **LQ-01 argv execution boundary: DONE.**
- STATUS: DONE.
- FILES_CHANGED: `aion_core/worker.py` (argv-based `check_command`/`run_command`, `DEFAULT_ARGV_ALLOW`, `HARD_DENY_BINARIES`, `SHELL_METACHARS`, `_argv_allow_names`, `_has_path_traversal`, `_check_binary_constraints`; `allow_command` now stores bare argv[0] names and refuses once `meta.policy_locked=="1"`); `tests/test_plan_worker.py` (rewrote the `mkdir&&echo` and `python3 -c` fixtures to argv-safe equivalents; added `TestArgvExecutionBoundary` with 5 new tests); `scripts/touch_marker.py` (new helper the rewritten fixture uses).
- TESTS: `python3 -m unittest discover -s tests -t . -q` → **212 OK** (was 207; +5 new tests, 0 broken).
- EVIDENCE: `grep -rn "shell=True" aion_core/` and repo-wide → no matches. `./aion scan .` → clean. `git diff --check` → clean. All 10+ injection strings in `TestCommandBlocklistHardening`/`TestArgvExecutionBoundary` raise `Refused`; `subprocess.run` verified (mocked) to be called with a list and `shell=False`.
- BLOCKERS: none.
- NEXT_ACTION: LQ-05 (runtime inventory) then LQ-03 (CI), per §15.

Session 3 — **`learnrepo` skill built (PREPARED, NOT MERGED).**
- STATUS: prepared on this branch, awaiting owner merge approval.
- FILES_CHANGED: `.claude/skills/learnrepo/**` (17 files: SKILL.md, 7 references,
  7 scripts, 1 asset, CHANGELOG), `tests/test_learnrepo_skill.py` (new, 46 tests).
- TESTS: full suite **258 OK** (212 → 258); official skill validator "Skill is valid!";
  `./aion scan .` clean; packages cleanly to `learnrepo.skill`.
- EVIDENCE: gate proven to fail closed on a blank manifest and to pass on a synthetic
  complete fixture; open critical finding vetoes perfect scores; execution without
  recorded containment blocks; static screen verified not to execute candidate code.
- BLOCKERS: none technical. Merge to `main` requires owner approval (RED band).
- NEXT_ACTION: owner decides OD-19 (merge learnrepo) — see §13.

Session 4 — **`smallest-fix` skill: written, tested, pushed (owner explicitly instructed push).**
- STATUS: DONE and pushed. This is NOT a learnrepo-gated action — it is original LucyOS-authored
  code, and the owner explicitly said "write independent LucyOS native version AND PUSH IT AFTER
  TESTING" after reviewing the learnrepo investigation of DietrichGebert/ponytail (which itself
  recommended "prototype", not merge -- see investigation `better-programmer-repo-eval`).
- WHAT: `.claude/skills/smallest-fix/` — a "write the smallest correct thing" coding-discipline
  skill, independently worded (not derived from ponytail's text/branding), backed by
  `scripts/check_reinvention.py`, an AST-based (never regex-over-text) checker that flags code
  reimplementing something `aion_core/util.py` already provides (UTC timestamps, id generation,
  sha256 hashing, atomic writes, JSON read/write).
- FILES_CHANGED: `.claude/skills/smallest-fix/{SKILL.md,CHANGELOG.md,scripts/check_reinvention.py}`,
  `tests/test_smallest_fix_skill.py` (new, 28 tests).
- TESTS: full suite **286 OK** (258 → 286); official skill validator "Skill is valid!"; `./aion scan .` clean.
- EVIDENCE: a real duplicate-finding bug (chained `hashlib.sha256(x).hexdigest()` reported twice) was
  found by testing against a synthetic fixture, fixed, and a regression test added. Self-check confirms
  `aion_core/util.py` is always exempt and the script never executes the file it scans.
- BLOCKERS: none.
- NEXT_ACTION: none required; available for use (`python3 .claude/skills/smallest-fix/scripts/check_reinvention.py <path>`).

## 11. REMAINING WORK (ordered; ids in EXECUTION_PACKAGE §9 / LOW_MODEL_TASK_QUEUE)

Phase 0: T-01/OD-03 disable desktop-commander (owner) · T-02/OD-01 visibility (owner) · T-03/LQ-05 runtime inventory · T-06/LQ-04 strategy-factory history scan.
Phase 1: T-04/LQ-02 backups (needs OD-05) · ~~T-05/LQ-01 argv boundary~~ DONE · T-07/LQ-03 CI · T-15/LQ-09 export/import.
Phase 2: T-08/LQ-10 non-root (needs OD-06) · T-09/LQ-11 remove unit · LQ-07 · LQ-08.
Phase 3: T-10/LQ-06 approvals v2 · T-11/LQ-14 manifests · T-12/LQ-20 policy root · T-13 broker (strong-model review) · T-14/LQ-15 telemetry · LQ-17 audit chain.
Phase 4–6: T-17/LQ-12 Radeon gate · T-16/LQ-13 FTS tables · T-18/LQ-18 document intake.
Strong-model-only items: broker interface review; injection red-team of intake; Phase-1 gate hardware re-decision; AMBER policy authoring with owner.

## 12. BLOCKERS

- No access to Mark-2/SCS.ADMIN01 from this session → runtime verification delegated (LQ-05).
- Owner decisions OD-01…06 pending (none block LQ-03, LQ-05, LQ-09, LQ-13, LQ-14, LQ-15, LQ-17 — start those; LQ-01 is done).

## 13. OWNER DECISIONS — see 06_OWNER_DECISIONS.md

NOW: OD-01 visibility · OD-02 buy nothing · OD-03 disable desktop-commander · OD-04 caps · OD-05 backup target · OD-06 non-root window. LATER: OD-07…18.

## 14. LOW-MODEL TASK QUEUE — see 05_LOW_MODEL_TASK_QUEUE.md (LQ-01…20, 16-field specs).

Unblocked right now for a cheap model: LQ-03, LQ-05, LQ-09, LQ-13, LQ-14, LQ-15, LQ-17, LQ-07, LQ-08. (LQ-01 done this session.)

## 15. EXACT NEXT ACTION

1. Owner: answer OD-01…OD-06 (or "accept all recommendations").
2. Cheap coding model: execute **LQ-05** (inventory script) → then **LQ-03** (CI). Commit each with the handoff format.
3. Worker with Mark-2 access: run `scripts/runtime_inventory.sh` (after LQ-05) and paste sanitized JSON into `EVIDENCE/`; update §2 of this file.
4. When OD-05 is answered: **LQ-02** backups, then the clean restore drill.
5. Strong model: only re-engage for T-13 broker review and the Phase-1 gate.

## 16. RESUME INSTRUCTIONS

```
git fetch origin claude/lucyos-architecture-audit-4o4q83
git checkout claude/lucyos-architecture-audit-4o4q83
cat docs/architect/CHECKPOINT.md            # this file
cat docs/architect/LUCYOS_ARCHITECT_EXECUTION_PACKAGE.md
python3 -m unittest discover -s tests -t . -q   # must say OK (212)
./aion scan .                                    # must be clean
```
Then take the next unblocked task from §15. Update §9/§10/§15 of this file and commit after every task. Do not reread the research ZIP; do not re-litigate ADRs without new evidence.
