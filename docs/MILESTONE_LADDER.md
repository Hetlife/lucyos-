# MILESTONE LADDER — the path to INR 1,00,000/month net, and where the wall is

_Artifact 2 of the Fable session, 2026-09-05. Every status below is measured
by `aion milestones` from `finance` rows with `stage='ACTUAL'`; nothing moves
on a forecast (enforced in `aion_core/milestones.py`)._

## The one-line answer

**The real wall is M3 (thirty hands-off days), not M6.** SevaaConnect sells
architecture and interior design. Selling, admin, follow-up, payment
reconciliation and reporting can all be hands-off today. Delivery cannot: a
human architect holds the call and draws the design. M0, M1, M2 and M4 are
reachable with the owner delivering. M3 requires either a delivery hire or a
productised offer that a junior produces from a template. M5 is where the
second project (the SEVAA Sales OS software itself, sold to other firms) has
the inverse profile: hands-off by construction, but a much harder M0.

## Rung by rung

| Rung | The number | Measured from | Capability needed | Exists today? | Owner time | Capital |
|---|---|---|---|---|---|---|
| **M0** first rupee | 1 ACTUAL revenue row with a payment id | `finance` | Take a payment, record it with evidence | **Yes** (Razorpay link + `aion money-add`; EXP-001 is the test) | ~4 h over 14 days | ₹0 |
| **M1** repeat payer | same `description` payer paid ≥ 2× | `finance` | A second thing the same buyer pays for: the project stage after the consult (site visit + concept, fixed price) | Partly: the offer exists on paper; EXP-002 defines it after EXP-001 | ~6 h per converted client | ₹0 |
| **M2** ten deliveries, positive net | ≥ 10 ACTUAL revenue rows, net > 0 | `finance` | Repeatable delivery of the consult and the first stage; costs recorded (`aion money-add cost`) | Yes for the machinery; **no** for volume: warm network alone yields ESTIMATE 3–6 paid in a month | ~25 h/month | ₹0 if warm network suffices; else first paid traffic ESTIMATE ₹10,000–15,000 over 2 months (own approval) |
| **M3** 30 hands-off days | `hands_off_days` meta ≥ 30 (recorded by the loop when the owner approves but never operates) | meta | Someone other than the owner delivers calls and briefs; the system schedules, invoices, chases | **No.** This is the wall. | 0 h/day by definition | Junior architect or interior designer in Gujarat ESTIMATE ₹25,000–40,000/month, or a productised deliverable a trained junior fills from `brief_template.md` |
| **M4** ₹25,000 net × 3 months | monthly net ≥ 25,000 for 3 consecutive months | `finance` | ≈ 10 consults/month, or 2 first-stage projects/month; a lead source beyond the warm network (T100 public funnel with a named traffic source) | Funnel built (S01/S06/S09), **not deployed** (T100 founder gate) | depends on M3 | Ads ESTIMATE ₹15,000/month once cost per enquiry is measured by EXP-004 |
| **M5** second business at M2 | 2 projects with ≥ 10 ACTUAL rows and net > 0 | `finance` grouped by `project` | Onboard a second project through `PROJECTS/REGISTRY.md` with its own `money_path.json` and experiments; no rewrite | **Yes** for the OS (registry, per-project money, experiments, money path are all project-keyed) | 4 h to define the offer | Candidate: SEVAA Sales OS as SaaS to other architecture firms at the modelled ₹14,999/month; ₹0 hosting on trial, then ESTIMATE ₹2,000/month |
| **M6** ₹1,00,000 net × 3 months | monthly net ≥ 1,00,000 for 3 consecutive months | `finance` | Delivery capacity of 3–5 first-stage projects/month plus consults, or 7 SaaS customers; the OS handles the rest | No: capacity, not software | — | Second delivery person ESTIMATE ₹30,000–40,000/month; working capital for modular/prefab is **out of scope** (large, slow, risky) |

## What the machinery can reach unassisted

- **Unassisted today:** everything that is state, routing, approval, recording,
  reporting and detection: M0 detection, M1 detection, M2 accounting, the
  phone and WhatsApp surfaces, plan execution by cheap models, the budget
  governor, the experiment verdicts.
- **With the owner delivering:** M0, M1, M2, M4.
- **Needs a capability that does not exist:** M3 (delegated delivery), and
  therefore any honest M6. The capability is a person or a productised
  deliverable, not code.

## Where capital must enter, and roughly how much

| When | What | Amount (ESTIMATE unless stated) | Gate |
|---|---|---|---|
| Now → M2 | Nothing. Warm outreach, Razorpay link, owner time. | ₹0 (VERIFIED: EXP-001 ceiling is ₹0 ads, ₹500 model spend) | none |
| After EXP-002 shows one consult→project conversion | First paid traffic test behind the public funnel | ₹5,000 cap for the first test, then ≤ ₹15,000/month | approval card; EXP-004 must measure cost per enquiry first |
| After M2 | Delivery hire or trained junior | ₹25,000–40,000/month | approval card; this is the M3 decision |
| After M4 | Second delivery person; SaaS hosting for M5 | ₹30,000–40,000/month; ₹2,000/month | approval cards |

Total capital before M4 is roughly ₹40,000–55,000 in the first three months
if the M3 hire happens early, and can be ₹0 if the owner accepts remaining the
deliverer until M2 proves the offer. The recommendation is the latter: do not
hire to deliver an offer that has not sold three times.

## What to stop believing

- That M6 is the hard part. It is a capacity problem once M3 is solved.
- That the public funnel is the next step. It is step 7 of the money path, after three warm payments.
- That the SaaS is the first business. It is the second, precisely because its wall is M0 and the services business's wall is M3; running both covers each other's weakness.
