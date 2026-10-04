# 19 — Roles, order and session structure for finishing LucyOS with Sonnet

Audit basis: `18_AUDIT_20261004.md`. Work orders: `work_orders/INDEX.md`.
This file is the operating manual. Each Sonnet session reads **this file §4–§6 and one work order**, nothing else from `00`–`18`.

## 1. Roles
| Role | Who | Does | Never does |
|---|---|---|---|
| **S-IMPL** | Sonnet, one fresh session per work order | implements one Sonnet-ready work order on its own branch, runs the gates, opens one PR | merges; edits protected or constitutional paths; adds dependencies or new `aion_core` modules unless the order says so; `git add -A` |
| **S-REVIEW** | Sonnet, a separate fresh session | reads the PR diff against the work order's acceptance tests, re-runs the gates, posts findings | pushes to the PR; approves on behalf of the owner |
| **FABLE** | high model | records overrides, re-freezes authority, reviews any order marked `Fable review: YES`, writes protected-path changes | mechanical work |
| **OWNER** | Het | merges, live probes on Lucy-den, decisions D-*, tags and branch deletes, secrets | — |
| **OPENCLAW** | Lucy-den | phone-side probes, morning routine | decides; forwards text without `lucy:` |
| **CODEX** | host-capable agent | census, deploys, restore drills | design |
| **DET** | scripts | ledger, index, boundaries, portability, tests | — |

## 2. Waves (dependency order; orders within a wave can run in parallel unless §5 says otherwise)

**Wave 0: owner on Lucy-den, about 30 min. This unblocks Level 2 and proves TR-1-08 live.**
1. `cd ~/lucyos-main && git fetch && git checkout --detach origin/main && ./aion boot`
2. TR-1-05 probe 3 and the masked evidence block (`work_orders/TR-1-05.md` step 3b/4). Paste the output to Fable.
3. TR-1-08 acceptance: `./aion work --max 1 --dry-run` on a READY test task, then one real run. The run must not report `CONTEXT_COMPILATION_FAILED`.
4. `./aion errors` → paste the output (ISSUE-044).
5. Repoint OpenClaw `LUCYOS_AION_BIN` to `~/lucyos-main/aion` (routine and forwarding).
6. PR #2: run the tag command in `work_orders/TR-C-05.md`, then close #2 (after the TR-C-05 PR merges).

**Wave 1: S-IMPL, code-only and protected-free (start now)**
| Order | Files (collision key) | Size |
|---|---|---|
| TR-C-05 PR #2 salvage record | `.lucy/archive/pr2-aion-whatsapp-control/README.md` | XS |
| TR-1-02 boundary ratchet → 0 | `aion_core/tasks.py`, `scripts/runtime_inventory.py`, boundary report path | S |
| TR-2-06 secrets escrow backup | `aion_core/backup.py`, `aion_core/cli.py` | S |
| TR-2-05 cost per verified task | `aion_core/metrics.py`, `reports.py`, `cli.py` (usage line) | S |
| TR-2-01 clean-machine proof | `scripts/clean_machine_proof.sh`, new test, `docs/OPERATIONS.md` | M |
| TR-C-02 archive contract skeletons | four modules, their tests, module manifests | S |
| TR-3-04 SCG/RPAB design banners | `docs/architecture/*` | XS |
| TR-6-03 verify_installed_services | new script, its test, `install_services.sh`. **Skip** the Mark-2 contract line (protected; leave a note in the PR) | S |
| TR-C-03 skill-system docs | `docs/ARCHITECTURE_GUARD.md`, archive Q000–Q005, `START_HERE.md`. **Skip** the `architecture.py` docstring (protected) | S |

**Wave 2: S-IMPL, after Wave 1 PRs touching the same files have merged**
TR-2-02 (Drive remote + nightly encrypted push; `bridges/drive_bridge.py`, `scripts/maintenance.sh`) · TR-I-01, then TR-I-02 (`api.py`, `http_server.py`, `web/`) · TR-4-06 (`cli.py`).

**F1: FABLE, in parallel with Wave 1.** One PR to `.lucy/authority/HIGH_MODEL_BASELINE.json` that records `task_overrides` for: TR-1-06, TR-2-04, TR-4-02, TR-4-05, TR-5-02, TR-5-03, TR-5-04, TR-5-06, TR-5-07, TR-6-04, TR-7-01, TR-C-01 (and TR-1-04 once D-5 is decided). Each override names the exact file globs from that order's Scope line. The owner merges it with admin bypass. **Do not re-freeze in F1.** The hashes will move again during Wave 3.

**Wave 3: S-IMPL after F1 merges. Every PR also gets a FABLE review.**
TR-1-06 → TR-4-02 → TR-4-05 · TR-2-04 · TR-5-01 (FABLE + OWNER ratify) → TR-5-02 → {TR-5-03, TR-5-04, TR-5-06, TR-5-07} → TR-5-05 · TR-6-04 · TR-7-01 · TR-C-01.
`db.py` is touched by TR-4-02, TR-4-05 and TR-5-02: **one at a time**, in that order (each adds a migration).

**F2: FABLE, after the last Wave-3 protected merge.** TR-0-03 re-freeze, so authority self reports 0 drift. That closes L1 together with TR-1-02 and TR-2-02.

**Wave 4: live, owner + CODEX + OPENCLAW.** TR-0-04 census → TR-4-03 · TR-2-03 restore drill · TR-6-01/02 · TR-8-01 token → TR-8-02 · TR-8-04 registration · TR-7-02 → TR-7-03 (L6) · then 14 days of TR-8-02/03 (L7).

**Owner decisions that gate orders:** D-5 → TR-1-04 · D-4 → TR-3-02/03 · D-8 → TR-C-04 · D-11 → TR-0-06 branch deletes · D-14 → Wave 4 Mac timing.

## 3. Critical path, one line
Wave 0 (L2) ‖ Wave 1 ‖ F1 → Wave 3 (TR-4-02 → L3; TR-5-* → L4/L5) → F2 (L1) → Wave 4 (L6, L7).

## 4. The S-IMPL session loop (low-level, follow exactly)
1. **Start clean.** `git fetch origin main && git checkout -b task/<ID>-<slug> origin/main`. Read the work order only. Then read the files its Scope line names.
2. **Apply the `smallest-fix` skill** (`.claude/skills/smallest-fix/SKILL.md`) before you write code. Grep for an existing twin. Stdlib only. If the order seems to need a third-party package, stop and use the `learnrepo` skill to write a research note. Never add the dependency.
3. **Protected check.** `python3 scripts/render_protected_paths.py`. If a file you must change is listed and the order has no recorded override, stop with `BLOCKED_HIGH_MODEL_DECISION: <path>`.
4. **Test first.** Write the failing test(s) from the order's acceptance list, run them, and confirm they fail for the right reason.
5. **Implement** the minimum that passes them.
6. **Gates (all must exit 0; paste real exit codes):**
   ```
   python3 -m unittest discover -s tests            # count must not drop vs main (864 at 13f5e11)
   ./aion scan .
   python3 scripts/check_portability.py
   python3 scripts/check_boundaries.py
   python3 scripts/verify_authority.py strict --base origin/main --branch task/<ID>-<slug>
   python3 scripts/verify_authority.py anti-dup --base origin/main
   ```
   `verify_authority.py self` is expected to report the known 6 drifts until F2. Do not try to fix those.
7. **Stage explicit paths only.** `git add <each file>`. Then `git status --short`: `evidence/` must stay untracked.
8. **Update the order's status.** Set its row in `work_orders/INDEX.md` to `PR #<n>` and add a one-line `**STATUS:**` at the top of the order file.
9. **Commit, push, open one PR** titled `<ID>: <title>`. The body is the result packet (§6). **Stop.** Never merge.

## 5. Collision and parallelism rules
- Two sessions may run at once only if their collision keys (Wave tables) are disjoint.
- `aion_core/cli.py` is shared by TR-2-06, TR-2-05 and TR-4-06: run them one after another, rebasing on `main` between them.
- Docs-only orders (TR-C-05, TR-3-04, TR-C-03) can run alongside anything.
- If `origin/main` moves during a session, merge `origin/main` into the branch (never rebase a pushed branch) and re-run the gates.

## 6. Result packet (PR body) and stop codes
```
STATUS: DONE | BLOCKED_HIGH_MODEL_DECISION | BLOCKED_OWNER | BLOCKED_EVIDENCE
ACTIONS: <3-6 bullets>
FILES_CHANGED: <list>
TESTS: <before/after counts, the new test names, real gate exit codes>
EVIDENCE_KEYS_ADDED: <or none>
BLOCKERS: <exact path or decision>
NEXT: <the next order this unblocks>
COST: executor=sonnet wall=<min> retries=<n>
```

## 7. Prompts

**S-IMPL (paste one per session; replace `<ID>`):**
> You are S-IMPL for LucyOS. Read `.lucy/planning/lucyos-total-recovery/19_SONNET_PLAN.md` sections 4–6, then `work_orders/<ID>.md`, then only the files its Scope names. Use the repo skill `smallest-fix` before writing code. Follow the §4 loop exactly: branch `task/<ID>-<slug>` from `origin/main`, test first, stdlib only, no protected or constitutional path without a recorded override (stop with `BLOCKED_HIGH_MODEL_DECISION: <path>`), stage explicit paths only (never `evidence/`), run every §4.6 gate and paste the real exit codes, update the INDEX status cell, open one PR with the §6 packet, and stop. Never merge, never print secrets.

**S-REVIEW (fresh session, after the PR opens):**
> You are S-REVIEW for LucyOS PR #<n> (work order `<ID>`). Read the work order and the PR diff only. Check each acceptance test against the diff and re-run the §4.6 gates on the PR head. Look for these specifically: protected-path edits, `evidence/` committed, a dropped test count, swallowed errors, secrets or absolute machine paths, and scope beyond the order. Post one review. Mark each finding blocking or optional, with file:line. Do not push.

## 8. Done means
- An order is done when its PR is merged with green CI and its INDEX row says `DONE (#n)`. Any live acceptance step must be recorded in `evidence/EVIDENCE_INDEX.md` or the order file.
- The program is done at L7: 14 consecutive days of nightly SEVAA reconcile plus a morning brief from the Mac primary, with authority self at 0 drift.
