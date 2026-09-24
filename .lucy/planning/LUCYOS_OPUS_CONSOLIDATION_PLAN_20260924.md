# LucyOS Consolidation Plan — aligned to the mission
Opus planning pass, 2026-09-24. Input: `LUCYOS_OPUS_PLANNING_BRIEF_20260924.md` (re-verified; one
correction in §6). Planning only — nothing merged, deleted, pushed or edited in protected paths.

## 0. The goal this plan is ranked against
AION `milestones`: mission **INR 1,00,000/month net**; M0 (first evidenced rupee) **not reached**.
`aion money-path`: **"no money path defined"**. Every engineering milestone so far (R-01→R-07) is
infrastructure. The repo has exactly one revenue path, and it is sitting unmerged on a branch.
So: **anything that moves the SEVAA revenue path onto `main` ranks first; hardware ranks last.**

## 1. Verified state (21:45 IST)
- `main` = `64e221b` (unchanged since PR #63). AION healthy, 0 errors, 12 done, A-104 only pending.
- Open tasks: `TASK-7FE6FC75` backup drill (blocked on A-103 passphrase), `TASK-61AB15F8` context/
  runtime cost (NEEDS_REVIEW), `TASK-C8F8DE5D` A-104, `TASK-12C0781A` LucyNest ("resume only on
  explicit LucyNest instruction").

## 2. Saved this pass (local only, nothing left the machine)
- `~/LucyBackups/lucyos-local-only-branches-20260924T214605.bundle` — **14 branches that existed
  nowhere but this disk** (verified `okay`), incl. M-CONTEXT-01/02, `task/lucy-progress-supervisor`
  (+13), `feature/lucynest-hid-backend-20260923` (+24), 4 security-redaction branches, local-ahead
  `feature/little-lucy-nebula-prep-20260920` (+27 vs +23 on origin).
- `~/LucyBackups/lucyos-base-checkout-dirty-20260924T214617.{tgz,patch}` — the 5 uncommitted
  paths in the base checkout ("preserved work"), untouched in place.
- Recommended durable copy: once A-103's passphrase exists, include these in the encrypted
  off-site backup. **Do not push them to the public repo unscanned** (the security branches
  carry secret-pattern fixtures).

## 3. Decisions needed from Het (numbered — reply D1=…, D2=…)
**D1 — SEVAACONNECT salvage (the revenue path). Recommend: YES, start now.**
`claude/fable-deploy-setup-mc5nr6` (32 new commits) holds `PROJECTS/sevaa-sales-os/money_path.json`,
EXP-001 paid-design-consult experiment, `aion_core/sevaa.py` (verified payments → AION revenue,
M0 from real cash), SEVAA approvals over WhatsApp, `phone.py` + `phone.html`. The authority
package already ruled: *"hold; selective salvage later (SEVAACONNECT deferred until consolidation
is stable); do not merge wholesale."* R-01→R-07 merged = consolidation is stable → precondition met.
Confirm: is SEVAA/SevaaConnect still the business, and is a paid design consult still the first
experiment? (`contacts.csv` is header-only — no PII.)

**D2 — LucyNest hardware. Recommend: stay parked; keep one ref, salvage non-hardware tips.**
Zero M0 contribution; task says resume only on explicit instruction. But the 7-branch cluster is
*not purely hardware*: shared base = 35 commits, and several sibling tips are core fixes
(`worker: skip empty-session churn`, `ci: fetch canonical main for context tests`, `ci: expose
failing unittest names`, remote-privileged-broker design doc, SCG device-key CLI). Keep
`feature/little-lucy-nebula-prep-20260920` + `feature/lucynest-hid-backend-20260923` as the parked
hardware line; review each sibling tip for a small cherry-pick PR; then retire the 6 siblings.

**D3 — M-CONTEXT-01/02: AION says DONE, code is not on `main`.** Only local branches hold it, and
the nebula branch contains *reverts* of it. Under the mission's own rule that's a false completion.
Choose: (a) open a PR from `review/M-CONTEXT-02-ratified-20260924` for review, or (b) declare it
superseded/abandoned and correct the two AION task records. Recommend (a) — it targets
`TASK-61AB15F8` (context cost), i.e. cheaper autonomous runs = cheaper path to revenue.

**D4 — Branch deletion, batched (nothing deleted until you approve a tier):**
- Tier A (62): fully merged into `main` — pure no-ops. (List: `git branch -r --merged origin/main`.)
- Tier B (4): authority-designated deletes (OWNER-03): `claude/aion-whatsapp-control-1seild`
  (strict subset of fable branch), `arch/lucyos-interface-m-a`, `candidate/mark2-loop-v1.2-20260908`,
  `feature/lucyos-aion-handoff`.
- Tier C (7): content already on `main` via PR #63 under different hashes: `task/R-04-…`,
  `task/R-05-…`, `task/R-06-…`, `review/autonomy-growth-main-…`, `feature/autonomy-growth-…`,
  `fix/ci-informational-drift-…`, `review/R-07-final-candidate-…`.
- Tier D (~20): needs a one-line verdict each before deletion (S-41..S-49 verified/ratified
  variants, `feature/resource-governor` vs S-03 `research_registry`, taskcheck pair,
  `research/codebase-reduction`, UI/UX research, Mac resolver, cerebras-e0). Do after D1–D3.
Net effect if A–C approved: ~113 → ~40 remote branches, all with a known purpose.

**D5 — Keep A-104 skipped?** Worth revisiting before D1 lands: SEVAA work puts business logic
(payment references, enquiry events) into a **public** repo. Recommend approving A-104 before
merging SEVAA, or keeping SEVAA project data out of this repo.

## 4. Execution order (Sonnet can run this; each step = own branch + PR, owner clicks merge)
1. Owner: A-103 passphrase (`./aion secrets set BACKUP_PASSPHRASE`, local terminal) → Sonnet runs
   `TASK-7FE6FC75` and adds `~/LucyBackups/*` to the encrypted off-site set.
2. D3: M-CONTEXT PR or AION correction.
3. D1: `task/S-SEVAA-salvage` from current `main`: bring over `PROJECTS/sevaa-sales-os/**`,
   `aion_core/sevaa.py`, SEVAA tests; resolve the 15 conflicts **preferring `main`'s re-implemented
   `intake.py`/`money_path.py`/`experiments.py`** (salvaged earlier via S-14/S-29); skip
   `deploy/fable/**` and `deploy/CODEX_*` (superseded prompts). Phone interface as a separate,
   later PR (token-gated API = exposure surface). Gate: full suite, scan, portability,
   authority strict/anti-dup, architecture-check (new module `sevaa.py`). Done-signal:
   `./aion money-path` prints the SEVAA path.
4. D2: sibling-tip salvage PR (non-hardware fixes only), then retire siblings.
5. D4 tiers A→C deletions, then Tier D verdicts.
6. Owner/high-model: authority re-freeze at the post-SEVAA SHA → name DC-1 → Mark-2 deploy, so
   the revenue loop runs on the canonical node rather than only on Lucy-den.

## 5. Guardrails unchanged
No self-merge; no protected-path edits (`.lucy/authority/**`, CI workflow, verifier); no Mark-2
access from Lucy-den; no branch deletion without an approved tier; no credentials in any chat.

## 6. Correction to the brief
The brief (§3) said the hardware branch's `aion_core/context.py` change (`--module/--budget-bytes/
--since/--json`) "may already be superseded by M-CONTEXT on main". **False** — `main` has none of
those flags, because M-CONTEXT never reached `main` (see D3).
