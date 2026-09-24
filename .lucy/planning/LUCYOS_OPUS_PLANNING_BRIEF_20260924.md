# Opus Planning Brief — LucyOS Post-R-07 Consolidation
Generated: 2026-09-24, by Claude Sonnet 5 (Claude Code), end of the R-05→R-07 repair session.
Owner: Het.

This is a **planning pass, not an execution session**. Read this in full before touching
anything. Live AION SQLite/runtime is operational truth; Git is code/version truth; this
file is a snapshot of both at handoff time — re-verify before acting on anything stale.

## 1. What just happened (verified, not assumed)

The R-05→R-07 repair mission (`.lucy/execution/repair-20260923/`) is complete and merged.

- `main` advanced `81d25a1` → `64e221b` (merge commit, PR #63, tree confirmed byte-identical
  to the fully-gated candidate `e8cc58d`).
- Contents merged: R-04 (owner-setup reconciliation), the autonomy-supervisor candidate,
  R-05 (OpenClaw↔AION proof), R-06 (reliability proof), R-07 (final evidence package).
- Post-merge, verified fresh on the actual `64e221b` commit: `aion health` healthy, 0
  unresolved errors, `aion verify --deploy-readiness` exit 0 (runtime verdict READY), 91
  targeted regression tests green.
- AION: `TASK-32820956` (R-04) and `TASK-351F4E80` (autonomy) marked DONE with this evidence.
- Approvals: A-101, A-102, A-103 recorded APPROVED in the canonical AION store (owner
  confirmed directly in this session; a parallel OpenClaw WhatsApp agent had only "noted"
  them without applying — see §4). **A-104 (repo private + protect main) intentionally
  skipped, owner's explicit instruction, not a rejection.**
- Full R-01→R-07 repair series is now DONE. `PROGRESS.md` in `.lucy/execution/repair-20260923/`
  reflects this (a small doc-only PR, `docs/progress-postmerge-20260924`, updates the last
  four rows to MERGED — check whether it landed).

## 2. What is still genuinely open (owner-only, not yours to execute)

1. **A-103's actual secret**: approval recorded, but the passphrase itself hasn't been
   provisioned. Owner must run `./aion secrets set BACKUP_PASSPHRASE` in a real local
   terminal (hidden `getpass` prompt — never through any chat channel, including this one).
   Only after that can the encrypted-backup+restore-drill task (`TASK-7FE6FC75`) run.
2. **Authority re-freeze**: `deploy_readiness.ready` is still `false`. Four protected files
   have hash-drifted from `fable_freeze_sha` `2a7002043cec` (`.github/workflows/lucyos-ci.yml`,
   `aion_core/config.py`, `aion_core/db.py`, `aion_core/router.py`) — **this predates the
   whole repair mission, is unrelated to anything merged today, and was never touched.**
   It needs an explicit owner/high-model re-freeze decision (`scripts/verify_authority.py
   freeze --sha <SHA>`) before any deploy SHA can be named. Do not "fix" it by weakening
   the verifier or baseline — that is explicitly forbidden.
3. **A-104** — still owner's call whenever they want it, not urgent.
4. **Mark-2 deploy** — `MARK2_DEPLOYMENT_CONTRACT.md` DC-1 is still `<<FABLE_NAMES_SHA>>`
   (unnamed). No deploy is authorized. Naming it is a Fable/owner ritual, not something
   either of us does. Lucy-den (this machine) has **no direct SSH/deploy access to Mark-2 by
   design** (`.lucy/planning/codebase-reduction-20260918/11_LUCY_DEN_MARK2_OPERATING_MODEL.md`)
   — don't try to reach it; read its state from committed evidence or what the owner pastes.
5. **`gh` CLI has no saved GitHub login on this machine.** PRs so far were opened by the
   owner clicking GitHub's own "create PR" links; a direct `git push` straight to `main` is
   explicitly blocked by Claude Code's own auto-mode classifier ("Merge Without Review") —
   that is a deliberate platform safety gate, not a bug, and the fix is the owner adding a
   permission rule in their own Claude Code settings, not a credential. A `gh auth login
   --web` attempt this session expired unused (code `2B03-74B6`, dead now) — worth retrying
   if the owner wants PR-creation automated (still requires a human merge click either way).

## 3. The branch landscape (the reason this brief exists)

The repo has **~113 remote branches**. A mechanical triage this session found:

- **62 branches are already fully merged into `main`** — pure no-ops, safe cleanup
  candidates (branch deletion needs owner approval per mission rules; nothing deleted yet).
- **~30 branches have only 1–2 unique commits** — mostly stale pointers to work already
  landed under different (rebased/cherry-picked) commit hashes; a few may be genuinely tiny
  unmerged items worth a quick look, not yet individually triaged.
- **One large tangled cluster (7 branches, 23–41 commits each, ~13,000-line diffs, almost
  entirely duplicate content of each other)** — confirmed to be the **LucyNest/Little Lucy
  hardware sub-project** (touchscreen display, physical touch probe, Nebula VPN device
  discovery, presence animation). `main` currently has **zero** hardware content. The
  mission's own backlog (`.lucy/execution/repair-20260923/` mission text referenced in the
  original handoff) says this stays **paused unless the owner explicitly reactivates it** —
  **do not merge any of this cluster without an explicit fresh owner decision to reactivate
  hardware work.** One incidental piece of this cluster touches `aion_core/context.py`
  (adds `--module`/`--budget-bytes`/`--since`/`--json` to `./aion context`) and may already
  be **superseded** by `M-CONTEXT-01`/`M-CONTEXT-02`, which AION's own task log shows DONE
  *today*, separately and more recently. Branch stack (base→tip), all forked from `66e3a4e`
  "owner: freeze governed MSOS candidate" (already on `main`):
  ```
  repair/scg-device-key-cli-20260920
    ├─ repair/ci-context-origin-main-20260920
    ├─ design/remote-privileged-action-broker-20260920
    └─ diagnostic/ci-full-suite-20260920
         ├─ integration/lucyos-autonomous-wave-20260919   (near-identical, 20 lines apart)
         └─ repair/worker-empty-session-churn-20260920    (near-identical, 20 lines apart)
    feature/little-lucy-nebula-prep-20260920 (sibling; this is what the base repo checkout
      at ~/GitHub/Hetlife/lucyos- is *currently sitting on*, with 5 uncommitted local paths
      the repo's own README says never to clean/reset — "unrelated preserved work")
  ```
- **Two genuinely different, much older branches, unassessed**: `claude/fable-deploy-setup-
  mc5nr6` (32 commits, base `f255ecc`, Sep 10) and `claude/aion-whatsapp-control-1seild` (28
  commits, same base, Sep 5). These predate a lot of what's since landed on `main` — need a
  from-scratch relevance check (is any of it still true, does it conflict, is it superseded),
  not a merge-with-the-hardware-cluster.

None of §3's cluster/triage work has been merged, deleted, or otherwise acted on. It is pure
survey. Full raw branch list with dates/authors is reproducible with:
```
git for-each-ref --sort=-committerdate refs/remotes/origin \
  --format='%(committerdate:short) | %(authorname) | %(refname:short)'
```

## 4. Things worth knowing that aren't obvious from the repo alone

- **There is at least one other active agent on this same machine** working this same
  mission in parallel via OpenClaw's WhatsApp "main" agent (workspace `~/.openclaw/
  workspace`, not this repo checkout — it cannot reach `./aion` or these git worktrees from
  where it runs). It gave the owner a stale/inaccurate status report this session (claimed
  approvals weren't recorded, claimed R-07 wasn't done — both were already true and correct
  in the canonical store by the time it said so). Not malicious, just working from a
  different, more limited vantage point. **Re-verify anything that agent reports against
  live state before trusting it**; don't assume it and this session share write access or
  a consistent view.
- **A separate stray branch, `feature/unlazy-completion-20260924`**, pushed by something
  else on this box, vendors a *different* copy of the `unlazy` skill and touches `web/` —
  367 files, -30,516 lines. Unrelated to this mission. Left untouched, worth a second look
  by someone before it's forgotten.
- **OpenClaw itself was reconfigured this session**: every agent (`main`, `lucy`,
  `learnrepo`) now defaults to `anthropic/claude-sonnet-5` via the `claude-cli` runtime
  (your Claude Pro/subscription login, not an API key), after the OpenAI/ChatGPT-Codex
  subscription hit a 3-day usage cooldown. This is unrelated to the LucyOS repo itself but
  is why the WhatsApp "main" agent behaves differently than it used to.

## 5. Suggested shape of the planning pass (not a mandate — use judgment)

1. Re-verify §1's facts still hold (things move fast on this repo; re-fetch, re-check
   `aion status`, re-check the approved-but-not-yet-executed items in §2).
2. Decide, and get the owner's explicit sign-off on, whether the LucyNest hardware cluster
   (§3) gets reactivated, stays parked, or gets formally archived/deleted. This is the
   single highest-leverage decision in the branch landscape — it's most of the unmerged
   branch count by far.
3. For the two old Fable/WhatsApp branches (§3), do the individual relevance check before
   recommending anything.
4. Produce a batched, owner-reviewable list of the 62 fully-merged branches (+ whichever of
   the hardware cluster's 6 duplicates get superseded by picking one) as deletion
   candidates — do not delete anything without the owner approving the batch.
5. Align whatever remains against the owner's actual goal for LucyOS — the AION objective/
   money-path records (`./aion money-path`, `./aion decide`, `NOTEBOOK.md`) are the source
   for what "our goal" concretely means; don't infer it purely from branch names.
6. Stop at the same owner-only gates this whole mission has respected throughout: no
   merge-without-review, no protected-authority edits, no credential/account changes, no
   Mark-2 access, no branch deletion without an explicit approved batch.

## 6. Read next, in this order

1. This file.
2. `.lucy/execution/repair-20260923/PROGRESS.md` (current mission state of record).
3. `.lucy/planning/codebase-reduction-20260918/11_LUCY_DEN_MARK2_OPERATING_MODEL.md` (why
   this machine can't reach Mark-2, and what Lucy-den is/isn't allowed to become).
4. `START_HERE.md` (repo root) and `.lucy/authority/HIGH_MODEL_BASELINE.json`
   (`owner_only_actions` — the hard stop list).
5. Live state: `./aion status`, `./aion health --deep`, `./aion approvals`, `git fetch
   origin && git for-each-ref ...` (§3's command).
