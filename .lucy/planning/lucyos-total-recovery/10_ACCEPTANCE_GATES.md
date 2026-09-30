# 10 — Acceptance gates: what "running" means

Every criterion is a command whose output is recorded in `evidence/` with a date. Current column is as of 2026-09-30 (EV-* keys).

| Level | Criteria (all required) | Current |
|---|---|---|
| **L1 ENGINEERING HEALTHY** | `unittest` OK on 3.9/3.11/3.13 + macOS; `clean-bootstrap-health` and `upgrade-from-main-schema` green; `check_portability` 0 violations; `check_boundaries` 0 violations; `aion scan .` clean; `verify_authority.py self` ok; every `main` SHA has a completed CI run; `.lucy/planning/INDEX.md` names one CURRENT plan; nightly encrypted backup exists off-host within 24 h | 7/10: authority drift (ISSUE-010), boundary warnings (ISSUE-015), cancelled main runs (ISSUE-013), off-host backup (ISSUE-021) |
| **L2 OPERABLE** | from the phone via OpenClaw: `status`, `tasks`, `approve <ID>`, `deny <ID>`, `pause`, `resume` each produce the expected DB change and an event carrying the principal/key id; `aion supervisor` snapshot visible on LucyNest/PWA; no shell access needed for a day of operation | not proven (ISSUE-011, ISSUE-027) |
| **L3 AUTONOMOUSLY USEFUL** | a 3-step PLAN (DET, A, B) applied with `aion plan apply` runs to DONE under `aion work`; the worker process is killed mid-run and `aion boot` + `aion work` finish it without duplication; each step has evidence; routing report shows the executor and INR per step; strong model not called | worker logic tested in CI; no live executor observed |
| **L4 PROJECT READY** | `aion project create X --workspace W` + `PROJECTS/X/project.json` yields an isolated project: tasks/memory/context/finance filtered by `--project X`; policy caps enforced (a C task under `max_model_class=B` is held); no `aion_core` file changed to create it; tests cover create/list/archive | ABSENT |
| **L5 COMPANY READY** | workspace with 2 projects and 1 integration; integration enabled on one project only and refused on the other; scoped secret resolved only inside its project; `aion health` shows the integration probe; revoke removes access and logs it | ABSENT |
| **L6 MAC PRODUCTION READY** | `07_` steps 3–11 executed on the mini: clean install, import, services survive reboot (3 launchd agents with PIDs), OpenClaw+WhatsApp round trip, nightly maintenance ran, `update.sh` applied and rolled back one SHA, Tailscale remote shell works, Lucy-den demoted | ABSENT |
| **L7 VALUE PRODUCING** | one real workflow (SEVAA reconcile + daily brief, or strategy-factory deliverable) runs on schedule 14 consecutive days; `aion usage` shows INR per verified task; owner rates ≥ 1 output/week as used; no manual repair sessions in the window | ABSENT (token missing) |

## Per-PR gate (unchanged)
Full suite + `./aion scan .` + `check_portability.py` + `verify_authority.py strict --base origin/main --branch <b>` + `anti-dup` + `check_boundaries.py` all exit 0; test count never drops; real exit codes reported.
