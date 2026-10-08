# Archive record: PR #2 `claude/aion-whatsapp-control-1seild`

PR #2 was **not merged**. Its head (`a9686060340bd803a145a0af6c5c22c7c4b1a149`, 2026-09-05) has no merge base with `main`, so GitHub reports it `dirty`; merging it would replace a month of `main` with a September snapshot. Decision and audit: `.lucy/planning/lucyos-total-recovery/18_AUDIT_20261004.md` §6; work order `TR-C-05`.

Preserved as tag `archive/pr2-aion-whatsapp-control` (owner pushes it; agent sessions cannot, ISSUE-046):

```
git fetch origin claude/aion-whatsapp-control-1seild
git tag archive/pr2-aion-whatsapp-control a9686060340bd803a145a0af6c5c22c7c4b1a149
git push origin archive/pr2-aion-whatsapp-control
```

Recover any file with `git show archive/pr2-aion-whatsapp-control:<path>`.

| Branch-only item | Decision |
|---|---|
| `scripts/backup_secrets.sh` | ported as TR-2-06 (stdlib, reuses `backup.encrypt_bytes`, no gpg) |
| `aion_core/metrics.py` `by_project`, `trend` | note for TR-5-03 / TR-I-01; not ported yet |
| `PROJECTS/sevaa-sales-os/bundles/{S01-enquiry-notify,S05-pointer-files,S06-source-attribution}.bundle`, `S04-branch-hygiene.sh` | owner/Codex: check whether branches `agent/coordinator/S05-pointer-files`, `agent/sales/S01-enquiry-notify`, `agent/sales/S06-source-attribution` exist in `het-life/sevaaconnect-realestate`; if not, apply per `bundles/README.md` on the tag |
| SEVAA planning docs (`AION_STATE.md`, adversarial review, task queue, handoff) | snapshot of 2026-09-03; the money path was salvaged by #71 |
| `aion_core/phone.py`, `bridges/web/phone.html`, `docs/PHONE_INTERFACE.md` | superseded by the `web/` Control Center and OpenClaw |
| `deploy/fable/*`, `deploy/CODEX_*.txt`, `scripts/codex_loop.sh`, `systemd/aion-codex.*` | superseded by the total-recovery package |
| shared files (router, worker, governor, approvals, ...) | older ancestors of `main`; nothing to take |
