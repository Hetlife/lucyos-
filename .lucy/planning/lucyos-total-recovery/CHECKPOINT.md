# CHECKPOINT — 2026-09-30 15:19 UTC (20:49 IST)

Resume here. This file supersedes chat history. Anything marked (reported) is what an agent or the owner said, not something Fable observed.

## Baseline
- `origin/main` = `8125fb8` (#53 UI/UX research docs merged last). Contains #73 context compiler, #88, #89 whatsapp verb, #90 strict approvals, #91 planning package, #92 CI no-cancel.
- Tests: 841 OK on the router-fix branch before #53 (docs only since). CI run #400 on `d9ea25a` was still running at last look; its result and the run for `8125fb8` were not observed.
- Lucy-den pulled to `78d08dd` (observed via owner paste), then to `8125fb8` (reported by OpenClaw). `aion boot` healthy; Ollama has 11 local models; OpenClaw reachable on 127.0.0.1:18789.

## Done today
Total system review and 52 work orders; deterministic tools (`scripts/branch_ledger.py`, `scripts/planning_index.py`); OpenClaw `whatsapp` verb (TR-1-03); router now decides approvals only on the exact `APPROVE <ID>` / `DENY <ID>` form (ISSUE-035, was a live hazard); CI no longer cancels main; OpenClaw morning routine live (job `e87c8c68-22d2-4af7-8217-146374e85641`, 08:00 IST, now `whatsapp "status"` and `"blockers"`, reporter only) (reported).

## In flight, in order
1. **Merge branch `fable/openclaw-forwarding-rule`** (docs only): `lucy:` marker rule in the OpenClaw skill, corrected TR-1-05, TR-1-07, ISSUE-038/039, this file.
2. **Owner, Lucy-den:** `./aion task-update TASK-77EAD62D --status CANCELLED` (stray task made by forwarding the word "pulled"; not confirmed done).
3. **TR-1-05 live E2E** (`work_orders/TR-1-05.md`): probe approval, four `lucy:`-prefixed messages, audit export, masked evidence. The pass condition that matters: `lucy: don't approve A-<n>` decides nothing. Not started.
4. **Codex TR-0-04 census** (now also reads previous-boot logs for the desktop freeze, `fwupdmgr` pending firmware, clock) and **TR-0-06** archive tags.

## Next after the E2E
TR-0-03 re-freeze (drift is 6 files and will change again; freeze after the last protected merge) · TR-1-06 (needs `worker.py` override) · TR-1-07 · TR-1-02 · TR-2-02 backup push · TR-2-04 root defaults (needs override; ISSUE-036 confirmed on Lucy-den) · TR-C-01/02 cleanup · TR-4-02 executor registry · phase 5 projects. Critical path: `17_CRITICAL_PATH.md`.

## Open issues found today
ISSUE-036 root-default `AION_HOME` on a non-root host (masked because OpenClaw exports it) · ISSUE-037 stale resume pointer · ISSUE-038 forwarding ambiguity (docs fixed, code guard TR-1-07) · ISSUE-039 OpenClaw skill copy goes stale after each pull · desktop freeze and uninstalled `linux-firmware` on Lucy-den (unexamined; census collects evidence, no fix yet).

## Owner decisions still open
D-4 LucyNest authority · D-5 bridge restart policy · D-8 retire the Fable launch pack · D-11 delete tagged branches, PRs #2 and #62 (open at last check) · D-12 first workflow · D-13 tunnel · D-14 Mac timing. Also delete remote branch `fable/FABLE-10-override-20260930` (redundant).

## Do not redo
The system audit, branch ledger, capability matrix, harness audit and cleanup register are done (`00`..`17`). Re-run `python3 scripts/branch_ledger.py` for branch state instead of re-reading branches. The Meta direct bridge, SCG crypto gateway, LucyNest touch hardware and any new frontend are off the critical path.

## Rules that stayed in force
Fable authors protected-path changes; the owner merges them with admin bypass. OpenClaw runs only `lucyosctl` verbs, forwards only `lucy:`-prefixed messages, decides nothing. Agents never merge, never delete remote branches, never print secrets.

## Save the AION-side checkpoint (owner, Lucy-den, after merging and pulling)
This also clears the stale resume pointer (ISSUE-037):
```
./aion checkpoint --objective "Make LucyOS operable from the phone via OpenClaw, then executors, then projects" --current-state "main 8125fb8, healthy, OpenClaw whatsapp verb live" --next-action "Run TR-1-05 live E2E, then Codex census TR-0-04" --last-verified-success "Router fix, whatsapp verb and CI fix merged; boot healthy" --bottleneck "TR-1-05 live approval proof not yet run" --files-to-read ".lucy/planning/lucyos-total-recovery/CHECKPOINT.md"
```

## Update 2026-09-30 17:50 UTC
- `main` = `4a41b0b` (#93 forwarding rule merged). The `lucy:` rule is in the skill and in TR-1-05 on main.
- Lucy-den's `~/lucyos` is on local branch `feature/question-context-reduction` with no upstream (observed), so `git pull` is a no-op there (ISSUE-041). Whether it contains the router fix is unverified: run the TR-1-05 preflight.
- Stray task `TASK-77EAD62D` is CANCELLED (observed). Two probe approvals exist and are PENDING: A-108, A-109.
- New blocker found in that task's `last_error`: ISSUE-040, imported `/root/...` session log paths make every compile fail, so `aion work` cannot run tasks on Lucy-den. The E2E does not depend on it. TR-1-08 fixes it.
- TR-1-05 reordered: the old order could not detect the old bug. Loose message first, against a pending approval.

## Update 2026-09-30 19:57 UTC
- Owner preflight: `~/lucyos` is at `8125fb8` (equal to main, router fix present, `decision_hint` count 2) but **dirty with a coding agent's uncommitted work** in `cli.py`, `context.py`, `model_gateway.py`. The verb path lives in `cli.py`, so the E2E must not run from there. Decision: run it from a clean detached worktree `~/lucyos-main` (proved on a scratch copy: the loose message returns "Nothing was decided" and leaves the approval pending).
- `main` moved again to include #62. After the E2E passes, repoint OpenClaw's `LUCYOS_AION_BIN` (routine and forwarding) to `~/lucyos-main/aion` permanently.
