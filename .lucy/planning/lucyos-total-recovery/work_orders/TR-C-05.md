# TR-C-05 — Resolve PR #2 by salvage and close (never merge)

**STATUS: OPEN.** Audit: `18_AUDIT_20261004.md` §6.
**Why:** PR #2 (`claude/aion-whatsapp-control-1seild` @ `a968606`, 2026-09-05) has no merge base with `main` and is `dirty`. Merging it would replace a month of `main` with a September snapshot. Its remaining value is in a few branch-only files.
**Current evidence:** `git merge-base origin/main a968606` → none; `branch_ledger.py` → UNRELATED; GitHub `mergeable_state: dirty`.
**Executor:** CLAUDE_CODE (Sonnet S-IMPL) for the record; OWNER for the tag and the close
**Scope:** new `.lucy/archive/pr2-aion-whatsapp-control/README.md` only: provenance (head SHA, date, PR link), the table below, and the `git show a968606:<path>` command to recover each file. Copy no code.
**Do not touch:** the PR #2 branch (it must exist until the tag is pushed); any code; `evidence/`
**Dependencies:** none

| Branch-only item | Decision |
|---|---|
| `scripts/backup_secrets.sh` | port the idea as TR-2-06 (stdlib, reuses `backup.encrypt_bytes`) |
| `aion_core/metrics.py` `by_project` / `trend` | note for TR-5-03 / TR-I-01; not ported now |
| `PROJECTS/sevaa-sales-os/bundles/S01, S05, S06` + `S04-branch-hygiene.sh` | owner/Codex check in `het-life/sevaaconnect-realestate` whether branches `agent/coordinator/S05-pointer-files`, `agent/sales/S01-enquiry-notify`, `agent/sales/S06-source-attribution` exist; if not, apply per the bundles README on the tag |
| SEVAA planning docs (`AION_STATE.md`, adversarial review, task queue, handoff) | archive pointer only (snapshot 2026-09-03; #71 salvaged the money path) |
| `aion_core/phone.py`, `bridges/web/phone.html`, `docs/PHONE_INTERFACE.md` | superseded by `web/` Control Center and OpenClaw; archive pointer only |
| `deploy/fable/*`, `deploy/CODEX_*.txt`, `scripts/codex_loop.sh`, `systemd/aion-codex.*` | superseded by the total-recovery package; archive pointer only |
| shared files (router, worker, governor, approvals, ...) | older ancestors of `main`; nothing to take |

## Steps
1. Write the README (Sonnet).
2. Owner, from any clone with push rights (agent sessions cannot push tags, ISSUE-046):
   `git fetch origin claude/aion-whatsapp-control-1seild && git tag archive/pr2-aion-whatsapp-control a9686060340bd803a145a0af6c5c22c7c4b1a149 && git push origin archive/pr2-aion-whatsapp-control`
3. Owner closes #2 with the comment: "Not mergeable (unrelated history). Preserved as tag archive/pr2-aion-whatsapp-control; salvage tracked in TR-C-05 / TR-2-06." The branch can then go with the D-11 branch deletes.

## Acceptance tests
- `git ls-remote origin refs/tags/archive/pr2-aion-whatsapp-control` prints `a968606...`
- README present; full suite OK, `./aion scan .` exit 0

**Security / rollback:** docs only; the tag keeps every byte recoverable
**Deliverables:** PR (README), owner tag + close
**Stop conditions:** the tag push fails for the owner → keep the branch, do not close #2
**Fable review required?** NO
