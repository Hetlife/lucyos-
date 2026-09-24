# LucyOS Prompt Work-Order Startup

Prompt files are versioned coordination work orders, not canonical memory, tasks, queues, approvals, or schedulers. Live LucyOS/AION SQLite remains operational truth; Git remains code/version truth; Drive is coordination/history.

1. Recover live LucyOS truth first: host, repo, branch/SHA, dirty state, runtime health, tasks/sessions, approvals and queue.
2. Read `.lucy/prompts/DRIVE_POINTERS.json`; use only the pinned Drive folder IDs. Do not create duplicate lifecycle folders.
3. Inspect `01_PROCESSING` before `00_PENDING`.
4. If exactly one prompt is PROCESSING, attach to its existing LucyOS task/session; do not create duplicates.
5. Otherwise inspect `00_PENDING` and start only an explicitly requested/eligible prompt.
6. Never execute an archived prompt automatically.
7. Use minimum context needed. Preserve starting SHA, task/session links, evidence and resume pointer.
8. PROCESSING requires verified existing task/session links in canonical AION.
9. On verified success: write result/evidence, mark COMPLETED, write an archive receipt, then move to `99_ARCHIVE` and mark ARCHIVED.
10. Archived work orders are historical evidence. Reactivation requires an explicit new owner instruction and must not silently reuse the old execution state.
11. Routine lifecycle handling is deterministic; do not call an AI/model merely to inspect or move state.
12. Never store secrets, raw credentials, private keys, or secret-bearing logs in Drive prompt artifacts.

Lifecycle: `PENDING -> PROCESSING -> COMPLETED -> ARCHIVED` with `BLOCKED`/`CANCELLED` as bounded alternatives. `02_COMPLETED` is a transient receipt/readback stage before archive.
