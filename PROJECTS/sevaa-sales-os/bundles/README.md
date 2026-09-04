# bundles/

SEVAA-side work produced by a session that cannot push to
`het-life/sevaaconnect-realestate` (the git proxy scopes credentials per
session owner). Each bundle is one task branch, built on `main` at `a85a8cc`,
with its own tests green and its commit message carrying full validation
evidence.

| Bundle | Branch | Task | Status |
|---|---|---|---|
| `S05-pointer-files.bundle` | `agent/coordinator/S05-pointer-files` | S05 | done, 36 passed |
| `S01-enquiry-notify.bundle` | `agent/sales/S01-enquiry-notify` | S01 (SEVAA side) | done, 45 passed |

Apply on any machine with push access, in this order:

```bash
cd sevaaconnect-realestate
git fetch <path>/S05-pointer-files.bundle agent/coordinator/S05-pointer-files:agent/coordinator/S05-pointer-files
git fetch <path>/S01-enquiry-notify.bundle agent/sales/S01-enquiry-notify:agent/sales/S01-enquiry-notify
git push -u origin agent/coordinator/S05-pointer-files
git push -u origin agent/sales/S01-enquiry-notify
```

Then open PRs and merge in the order given in `../AION_TASK_QUEUE.md`. S01's
SEVAA-side branch should merge only alongside the AION-side commit
(`0dc7888` on `Hetlife/lucyos-`) — the two halves are one contract.
