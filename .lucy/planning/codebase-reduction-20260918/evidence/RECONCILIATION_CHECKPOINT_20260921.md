# LucyOS reconciliation checkpoint — 2026-09-21

## Repository state

- Canonical `main`: `66e3a4e` (`origin/main`); SCG is not present there.
- Lucy-Nest branch: `feature/little-lucy-nebula-prep-20260920`.
- Lucy-Nest HEAD: `facb67c` before this checkpoint; local and remote matched.
- Integration remote: `55546fe82ddfba25e527df237766ae7c09346389`.
- Exact clean integration worktree: `/tmp/lucyos-reconcile.LUxbPe` at `55546fe`.
- Named `/home/scs-admin01/GitHub/Hetlife/lucyos-integration` worktree: clean but stale at `897c453`; no unique commits found. Preserved pending cleanup approval.

## Lucy-Nest classification

- Versioned source/config/design: `src/`, `index.html`, `vite.config.ts`, `theme/`, `harness/`, `package.json`, `package-lock.json`, `tsconfig.json`, product docs.
- Regenerable and now ignored: `dist/`, `node_modules/`, `runtime/little-lucy/state.json`, `current.jpg`, `frames/`.
- Tracked cache needing a separate untracking decision: `packages/lucy-nest-design-system/tsconfig.tsbuildinfo`.
- Operational source preserved: runtime shell/Python helpers.
- `docs/repo-intelligence/`: generated analysis snapshot from commit `1dbda69`; includes `build_indexes.py` plus derived JSON indexes. Not committed or deleted; recommended `KEEP LOCALLY` or upload as evidence after regeneration against current source.
- `runtime/little-lucy/lucy-nest-rsa.pub`: referenced by `bootstrap-lucy-nest.sh`; retained. No private key was searched for or exposed.
- `runtime/little-lucy/nebula-client.sh`: operational source candidate, untracked; preserved pending ownership decision.

## Worktrees

- Active/current: Lucy-Nest feature worktree.
- Complete but unclosed: S-41 through S-49 task worktrees and SCG device-key worktree; clean, remote branches exist.
- Stale but preserved: named integration worktree at `897c453`.
- Dirty/preserved: M5 worktree at `1fff24a` with runtime changes.
- Prunable candidates: missing `/tmp` worktree directories whose git metadata is marked prunable. Not removed.
- Unknown/owner review: no worktree was deleted because process/session ownership was not independently proven.

## SCG on exact integration SHA

- SCG files present; feature flag in the local AION runtime reports enabled and `lucy-den` enrolled ACTIVE. This is prior local runtime state, not a main-branch promotion; no flag was changed.
- Targeted gateway suite: 9/9 pass under the pinned SCG venv with isolated `AION_HOME`.
- Full unittest run: bounded run emitted expected environment/fixture diagnostics but did not complete within the available command window; no full-suite PASS is claimed here.
- Status: validated on integration, not activated as a deployment, and not main-compatible/established.

## Health and owner gates

- Gateway, RDC, Ollama and Drive were previously live; no changes made.
- No merge, force-push, activation, credential change, deletion, worktree pruning, or public exposure performed.
- Owner gates remain: ambiguous worktree deletion/pruning; tracked cache untracking; public-key retirement; SCG activation; main promotion.

## Verification update

- GitHub transport repaired without credential rotation: existing `github-account-1` now uses official `ssh.github.com:443`, preserves the existing host-key alias, and disables the stalled SSH agent for this alias only.
- SSH authentication: PASS; `git fetch`: PASS; branch push: fast-forward/no-op; remote branch verified at `7f46204`.
- Exact integration `55546fe`: SCG targeted tests 9/9 PASS; full dependency-enabled unittest suite 627 tests, 10 skipped, PASS; portability PASS; secret scan PASS; boundary scan 0 violations/0 stale; live `aion verify --json`: READY.
- Isolated-temp `aion verify` is intentionally not used as a health verdict because it lacks the machine's shared brain, secret store and backups; live AION_HOME verification is READY.

## Next action

Obtain owner direction for the clearly identified cleanup candidates, then separately complete a full-suite run on exact integration `55546fe` with a bounded environment and reconcile the named stale integration worktree.
