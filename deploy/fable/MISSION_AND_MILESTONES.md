# MISSION AND MILESTONES

## Mission
INR 1,00,000 per month of real, owner-withdrawable **net** profit.

## How a milestone is allowed to move
Only from rows in the `finance` table with `stage='ACTUAL'` and non-empty
`evidence`. A forecast, a pipeline value, a sandbox run or a test payment never
moves a milestone. This is enforced in `aion_core/milestones.py`, not by policy,
and the major ones (M0, M2, M4, M6) stop the build loop so
the owner decides what happens next.

## The ladder, and where it actually stands right now

| Milestone | Status | Measured by |
|---|---|---|
| M0 | not reached | 0 evidenced revenue row(s) |
| M1 | not reached | largest payer count: 0 |
| M2 | not reached | 0 evidenced deliveries, net INR 0 |
| M3 | not reached | 0 hands-off days recorded |
| M4 | not reached | 0 consecutive month(s) at INR 25,000 net |
| M5 | not reached | 0 project(s) with positive proven economics |
| M6 | not reached | 0 consecutive month(s) at INR 1,00,000 net |

## What each one means

- **M0** — the first evidenced rupee. One real revenue row.
- **M1** — one payer has paid at least twice. Repeatability, not luck.
- **M2** — ten evidenced deliveries and positive net. A real, working offer.
- **M3** — thirty recorded hands-off days. The system runs without the owner.
- **M4** — three consecutive months at INR 25,000 net.
- **M5** — two projects each independently at M2 economics. Not one lucky offer.
- **M6** — three consecutive months at INR 1,00,000 net. The mission.

Be honest in your analysis about which rung is the real wall. It is rarely the
last one, and naming the wrong wall wastes everything downstream of it.
