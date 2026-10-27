# LucyOS context recovery — October 27, 2026

Verified main baseline: e349bb03446452bace3a5225d990a73bae8160e1. This is a **candidate**, not a deployed protected merge. Live worktree: `/home/scs-admin01/lucyos-context-20261027`; preserve that local dirty state until reconciled.

## Live findings
- Lucy-den AION status HEALTHY; 0 ready, 0 running, 2 blocked, 24 done, 0 unresolved errors at observation time; 41 tasks in SQLite.
- OpenClaw 2026.9.4 and WhatsApp, three Telegram transports connected. 43 OpenClaw sessions; cumulative session counters include 212,474 (main) and 269,060 (Lucy). These are NOT measured single-prompt tokens.
- OpenClaw session pruning applied by native validated configuration: `agents.defaults.contextPruning={mode:"cache-ttl",ttl:"5m"}`. Existing safeguard compaction retained; backup restricted locally. No production cost savings claimed.
- AION already has the M-CONTEXT-02 bounded compiler integrated at the existing worker; no new scheduler. ISSUE-030/TR-1-06: DET `exec_command` tasks are unnecessarily blocked on compiler availability. Protected `worker.py` needs its existing Fable/owner override, not unauthorized modification.
- **New code fix:** existing `context.build` repeated full `PROMPT FOR THE EXECUTING MODEL` text that the worker already prepends. Retain instruction once and replace duplicate with SHA256 digest pointer. Synthetic 9 KB directive: 19,374 → 10,430 bytes (46.2% less), NOT measured all-in production token savings. Four regression tests and existing context-contract tests passed; complete Lucy-den suite 817 tests passed (one skipped).
- Learned first-hand: LearnRepo Telegram transport healthy while execution failed. Existing Claude CLI primary exhausted weekly quota; OpenCode fallback failed HTTP 401. Existing OAuth-supported `openai/gpt-5.6-sol` returned successful isolated response; LearnRepo-specific primary changed to it, invalid fallbacks removed via validated native config, with separate 0600 backup; fresh route returned `LEARNREPO_READY`. Telegram end-to-end delivery is a separate gate.
- Read-only installed-unit audit: `aion-bridge.service`, `aion-interface.service`, `aion-maintenance.service`, `aion-work.service` differ from checked repository templates; both associated timers match. Do not restart blindly.
- After fresh public fetch, the deterministic branch ledger shows 141 remote branches vs main: 77 CONTAINED, 8 PATCH_IN_BASE, 56 UNIQUE. Classify semantic value before integration, tag before any owner-approved deletion.
- Mark-2 primary remains older and dirty; no promotion. Both hosts previously reachable; Lucy-den Remote Desktop became temporarily unresponsive during final packaging, with all local edits preserved.

## Canonical task inventory and merge path
The existing [55-work-order index](work_orders/INDEX.md) is the canonical recovery execution program (status labels last refreshed Oct 4). Do not duplicate it.

| Wave | Existing task IDs | Current remaining gate |
|---|---|---|
| Reality/authority | TR-0-01..06, TR-1-01..02 | Main CI, authority re-freeze, branch ledger/cleanup |
| Context/agents | TR-1-06, TR-2-05, TR-4-01..06 | DET compiler decoupling, cost telemetry, live independently verified model tasks |
| Owner channel | TR-1-03..08, TR-3-01..04, TR-I-01..02 | Actual approve/deny and scoped write through phone UI |
| Backup/restore | TR-2-01..06, TR-6-01..04 | Escrow fix, off-host restore, rendered systemd parity and controlled deployment |
| Companies | TR-5-01..07, TR-8-01..04 | Project policy, scoped integrations, first evidenced revenue |
| Mac | TR-7-01..03 | No promotion until launchd and parity verified, explicit owner approval |
| Cleanup | TR-C-01..05 | Classify, tag, archive without deleting live work |

Live AION review/holds to reconcile (not automatically ready): TASK-B834A540 (Mac); TASK-0EFD9D45 (paid provider routing); TASK-9779ACE3 and TASK-F9A07C9C (off-machine backup owner gate); TASK-2A914DCE (mobile console write); TASK-A9040767 (financial evidence); TASK-AB21B296 (Prefabulas demo); TASK-89B0270A (LearnRepo org-wide health, deferred); S-48 (boundary merge); TASK-F8F6917D (owner-only approvals); TASK-3A07D915 (Meta token scanner, protected); TASK-7AC78CC8 (LearnRepo skill reviews). TASK-66B1FF66 is a physical camera diagnosis, not an OS deployment blocker.

Open review PRs: #105 (index isolation), #106 (failure propagation), #109/#110 (service verification; dedupe), #111 (agent harness), #108→#102 (escrow safety then backup), #107 (baseline). Owner approval required before protected merge.

Known stale duplicate branches/features: historical `feature/context-pack` (third context path), second `feature/resource-governor`, old standalone TaskCheck, outdated `unlazy-completion` vendor core. Use existing AION, LearnRepo, OpenClaw and business-project boundaries.

## Real earning — no fake income
`PROJECTS/sevaa-sales-os/experiments/EXP-001-paid-design-consult` already defines a ₹2,499 warm-contact design consultation pilot; `aion money-path` showed 2/8 completed, next steps owner payment-link validation then consent-based direct outreach to 30 warm contacts. No evidenced sale yet. Strategy Factory was at 0/11 money-path and remains research/paper until independent tests and separate capital authorization. Do not equate repo code with sales.

## Next acceptance gates
1. Current CI-green context PR and #105/#106/#111 integration under owner authority; no blind merges.
2. Live per-request prompt/token telemetry and comparison including retries, not just static byte counts.
3. LearnRepo Telegram generated reply and provider reliability; preserve failed session history.
4. AION claim→context→verified executor→test→DONE→owner notification→restart E2E.
5. Verified encrypted off-machine restore and service parity before Lucyd-en code promotion; Mark-2 remains secondary.

Rollback: local native OpenClaw configs backed up under restricted `~/.openclaw/backups` paths; context builder patch is reversible via its isolated Git branch. No protected runtime file was modified by this PR.
