# 00 — Fable Executive Summary: LucyOS Codebase Reduction / Autonomous Repair Program

Fable strategic-architecture pass, 2026-09-18. Planning base: `origin/main` @ `66e3a4ef1b8242123555af5a7c9d80115ab23d82`
("owner: freeze governed MSOS candidate", CI run 35279040189 green). No code was changed by this pass.

Inputs read in full: `FABLE_LUCYOS_AUTONOMOUS_REPAIR_ARCHITECTURE_MASTER_PROMPT.txt`,
`DEV_LUCYOS_CODEBASE_REDUCTION_EXECUTION_PLAN.md`, `Executive Summary.pdf`, the Lucy Codebase
Reduction Skill (`Safari.pdf`), plus the owner's Drive doc `01_CURRENT_STATE_BASELINE` (2026-09-18 05:23Z).
Live evidence: canonical `main`, 49 remote branches, GitHub PRs/CI, an isolated `AION_HOME` run of
`./aion init/seed/health/capabilities/context/route/architecture-check`, and a fresh full test run.

## The one-paragraph answer

LucyOS is **not** a 150–200k-LOC monolith that agents cannot fit in context. It is a 20.6k-LOC Python
kernel plus ~30k lines of governance, manifests, skills, planning and docs, and the *planning/governance
text is what agents actually drown in*. The repo already contains every mechanism the documents propose
to build — task queue, approvals, checkpoint/resume, model routing, context packets, architecture guard,
authority baseline, deterministic verifier, session logs, sync packets — so the program is a **repair and
wiring** program, not a construction program. The single most important live fact the documents missed:
**both Lucy-den and Mark-2 run `feature/resource-governor` @ `2cd3cc5`, 136 commits behind canonical
`main`**. Until that is reconciled, no measurement taken on a node describes the code the owner froze.

## Ten decisions this package makes (details in the numbered files)

1. **Direction:** hybrid modular monolith — one repo, one SQLite, logical module contracts enforced by a
   ratchet, skill manifests as the extension seam. Option C (services/repo split) is rejected for this
   cycle; Option B is not a separate option here because the manifest mechanism already exists (02).
2. **Authority chain, corrected:** `OWNER → FABLE → CONTROLLER (ChatGPT/DEV) → WORKERS → VERIFIER`, with
   **Lucy-architect-audit as a mandatory gate stage, not a layer of command** — it is executed by
   deterministic tools (`verify_authority.py anti-dup|strict`, `check_portability.py`, `aion scan`,
   `aion architecture-check`) plus a high-model review for what the tools cannot judge (04).
3. **Autonomy levels L0–L5** mapped onto existing machinery: `HIGH_MODEL_BASELINE.json` protected paths,
   `approvals.py`, `tasks.STATES`, C5 GREEN/AMBER/RED bands (04).
4. **No new queue/state/scheduler.** The dev task graph lives in git (`06_TASK_GRAPH.json`, same precedent as
   `SONNET_TASK_QUEUE.md`); execution state lives in PR bodies and `CHECKPOINT.md`; Mark-2's AION stays the
   only canonical runtime queue (05, 11).
5. **Task IDs must match the verifier regex** `(S|FABLE|OWNER|CODEX)-\d{1,4}`. Reduction tasks are
   `S-40…S-59`; a `CR-` prefix would silently escape the strict gate (04, 08).
6. **Context strategy:** extend `aion context` (exists, DB-driven) with a repo-aware module section; salvage
   the delta/watermark idea from `feature/context-pack`'s `context_pack.py`; **do not** build
   `context_pack_builder` / `task_context_profiler` as skills — the first is an extension, the second a
   deterministic script (09).
7. **Verifier independence:** author ≠ verifier ≠ approver for every L2+ change; Codex-authored →
   Claude-verified (or vice-versa) → CI → controller merges only into the research branch; owner merges
   to `main` (04, 05).
8. **Failure loop:** three materially different attempts, then `BLOCKED_TECHNICAL` with an evidence packet
   to Fable. Same numbers as `config.MAX_TASK_RETRIES=3` and `worker._fail`'s escalation at two (05).
9. **Recovery:** every task ends with a commit to `CHECKPOINT.md` + `TASK_GRAPH.json`; a fresh session
   resumes from those two files, open PRs and `git status` — never from chat (05, 13).
10. **Exit:** M9 VALUE MODE is a hard gate with numeric criteria; after it, P4/P5 self-improvement is capped
    at ≤20% of controller cycles (07, 14).

## What is stale in the inputs (full table in 01)

- Executive Summary: "150–200k LOC", "hundreds of modules", "`task_context_profiler`/`context_pack_builder`
  to be written", "`codex_runner`/`claude_runner`/`code_inspector` skills in LucyDB" — none exist; the
  skills catalog has 104 *manifests*, of which 9 are registered/enabled on a fresh home.
- DEV plan: "Mark-2 remains canonical runtime" is a policy, not a fact — Mark-2's checkout is not `main`.
- Both: "Lucy-architect-audit before every code change" names a *process*; the runnable
  `aion architecture-check` validates a skill-proposal JSON and its catalog entry is `enabled: false`.
- The 2026-09-17 audits' open items (allowlist, `semantic_recall` SQLite ruling, promotion to `main`) are
  **all resolved** on `main` as of `f2f1211`/`2a70020`/`66e3a4e`.

## What ChatGPT/DEV executes first

`S-40 — M0 canonical baseline lock` (L1, no code): record `main` SHA, CI run, test count/time, node
checkouts, open PRs, branch inventory into `evidence/M0_BASELINE.md`; then raise `OWNER-06` (node
checkout policy). Full card and acceptance criteria in `16_FIRST_10_TASKS.md`; the controller prompt
that drives it is `17_CHATGPT_MASTER_EXECUTION_PROMPT.txt`.

## Files in this package

| # | File | Covers master-prompt items |
|---|---|---|
| 00 | this file | — |
| 01 | `01_GROUND_TRUTH_RECONCILIATION.md` | §5 reconciliation |
| 02 | `02_ARCHITECTURE_OPTIONS_AND_RECOMMENDED_DIRECTION.md` | 02 + 03 |
| 04 | `04_AUTHORITY_MODEL.md` | 04 + 15 (owner approval matrix) |
| 05 | `05_AUTONOMOUS_EXECUTION_LOOP.md` | 05 + 13 (failure/retry, checkpoint/recovery, rollback) |
| 06 | `06_TASK_GRAPH.json` | dependency-aware DAG |
| 07 | `07_MILESTONE_GATES.md` | M0–M9 |
| 08 | `08_TASK_CARD_TEMPLATE.md` | §16 schema |
| 09 | `09_MODEL_TOOL_ROUTING_AND_CONTEXT_STRATEGY.md` | 09 + 10 |
| 11 | `11_LUCY_DEN_MARK2_OPERATING_MODEL.md` | §15 |
| 12 | `12_RISK_REGISTER.md` | risks |
| 14 | `14_METRICS_SCORECARD.md` | §23 |
| 16 | `16_FIRST_10_TASKS.md` | §13 + acceptance criteria |
| 17 | `17_CHATGPT_MASTER_EXECUTION_PROMPT.txt` | §17 (the deliverable) |
| 18 | `18_WORKER_AND_VERIFIER_PROMPTS.md` | 18, 19, 20, 21 |
| 22 | `22_GOOGLE_DRIVE_ARCHIVE_PLAN.md` | §20 |
| 23 | `23_FINAL_HANDOFF.md` | §26 (25 questions answered) |
| — | `CHECKPOINT.md` | live controller checkpoint (starts empty) |
