# 12 — Risk Register

| ID | Risk | Likelihood | Impact | Mitigation (where) | Trigger to escalate |
|---|---|---|---|---|---|
| R-01 | Nodes keep running `2cd3cc5` while the program measures `main`; conclusions do not describe production | High (it is the case today) | High | OWNER-06 at M0; all measurement in detached `main` worktrees; M9 entry criterion (5) | any "Mark-2 evidence" quoted without its SHA |
| R-02 | Controller creates a second queue/state (e.g. a dev AION DB it starts treating as truth) | Medium | High | 05 §1: git task graph is the queue; local `AION_HOME` declared disposable; anti-dup blocks code-level duplicates | a checkpoint block cites a DB row as authority |
| R-03 | Task IDs with a non-matching prefix silently bypass `strict` | Medium | High | 08: `(S|FABLE|OWNER|CODEX)-\d{1,4}` only; S-40 acceptance includes a dry-run of strict on an empty task branch | strict reports "task id undeclared" on a branch that has one |
| R-04 | "Architecture audit" is treated as a checkbox because the runnable only checks skill proposals | High | Medium | 04 §3 defines the gate as tools + high-model checklist; card field `ARCHITECTURE_AUDIT_REQUIRED` records who answered | a card with `pre: PASS` but no named reviewer |
| R-05 | Author verifies own change (Codex writes, Codex "reviews") | Medium | High | 04 §1 correction 2; 05 INDEPENDENT step; PR body must link a verifier report by a different executor | verifier field equals executor |
| R-06 | Infinite rework on one task | Medium | Medium | 05 §4: 3 attempts, root-cause note before attempt 2, class change before attempt 3, then `BLOCKED_TECHNICAL` | attempt counter ≥ 3 |
| R-07 | Scope creep into protected paths under a "refactor" label | Medium | High | strict gate; card `FILES_FORBIDDEN` always lists protected paths; L3 requires a baseline override written *before* work starts | strict fails on a task branch |
| R-08 | `check_boundaries.py` false positives block CI | Low (warning mode first) | Medium | 07 M4: ≥ 5 days warning mode, 0 FP before promotion; owner promotes | any FP after promotion → demote immediately (owner) |
| R-09 | Text-corpus archiving deletes something a directive/contract points to | Medium | Medium | S-50 test greps every referenced path; archives are moves; deployment contract and `.lucy/authority` are read-only for the task | a broken link test fails |
| R-10 | Owner becomes the bottleneck for L2 merges to `main` | High | Medium | L2 work merges into the research branch autonomously; only S-45/S-47/S-49/S-53/S-55 need `main`; controller batches owner asks per milestone | > 3 `MERGE_CANDIDATE` PRs older than 7 days |
| R-11 | `feature/context-pack` merged wholesale (18k-line stale diff) | Low | High | 09 §2: port the idea, close the branch | a PR from that branch |
| R-12 | Program never ends (permanent self-improvement) | Medium | Medium | M9 numeric entry criteria; 20% cap on P4/P5 afterward; new architecture work needs a measured regression | > 2 weeks past M9 criteria without VALUE MODE |
| R-13 | Local models produce plausible-but-wrong classifications that enter manifests | Medium | Medium | class-A output is reviewed by a B worker before commit; S-44 coverage test catches ownership errors | manifest test fails |
| R-14 | Secrets/private paths leak into evidence or Drive | Low | High | `./aion scan .` on every commit; packs are `security.redact`ed; Drive receives only files that are also in the public repo | scan finds content |
| R-15 | `main` moves under an open task branch (owner works in parallel) | High | Low | 05 §6: merge `origin/main` into the branch, never rebase; re-run gates | conflict on merge |
| R-16 | Executive Summary's estimates re-enter planning as facts | Medium | Low | 01 marks them STALE; the controller prompt forbids citing them | a card cites "150k LOC" or a "to be written" skill |
| R-17 | Codex on Lucy-den lacks a tool the card assumes (e.g. no `ollama`) | Medium | Low | cards name stdlib-only commands; `aion capabilities` on the node before dispatch | worker packet BLOCKERS names a missing tool |
| R-18 | CI `authority-gate` runs only on PRs, so direct research-branch commits skip anti-dup | High | Medium | controller runs anti-dup/strict locally before every research-branch merge (05 REGRESSION); L2 code always via PR | a research-branch commit touching `aion_core/` without a PR |
