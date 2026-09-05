# EXP-001 — Paid design consultation to warm contacts

_Artifact 1 of the Fable session, 2026-09-05. Written to be decided by numbers,
not by feel. Everything marked UNKNOWN is a fact the owner can supply in under
ten minutes; nothing below is guessed in its place._

## One offer, one channel, one buyer

| | |
|---|---|
| **Offer** | "Design Clarity Call": a 90-minute consultation with SevaaConnect (architecture / interior) plus a one-page written brief within 48 hours: recommended layout direction, realistic budget range, next three steps. The full fee is credited against any SevaaConnect project the buyer signs within 90 days. |
| **Price** | **INR 2,499 including GST**, paid up front through a Razorpay payment link, before the call is scheduled. |
| **Buyer** | One person who owns or is about to take possession of a home or a small commercial unit in Gujarat and is planning interiors, renovation or a small build in the next 6 months. |
| **Channel** | The owner's own warm network on WhatsApp: a personal message, one at a time, to at least 30 named contacts. No broadcast lists, no ads, no public post. |
| **Project key** | `sevaa-sales-os` (this folder). Nothing here touches `aion_core/`. |

## Why this and not the public funnel

The SEVAA quote funnel is built and tested but unreachable: T100 (public
deployment) is gated on five founder actions and, even once open, has no
traffic source. Opening it first means paying for traffic before knowing whether
anyone pays for anything. This experiment inverts that: it tests willingness to
pay with zero deployment, zero ad spend, and the machinery already in the repo
(`aion money-add` with a Razorpay payment id as evidence flips M0 through
`aion_core/milestones.py`). If nobody in the warm network pays INR 2,499 for a
consultation, a cold funnel will not convert at 10× the cost.

## Hypothesis (stated so it can be false)

> Of the first 30 warm contacts personally messaged with the offer, at least 3
> will pay INR 2,499 through the payment link within 14 days of the first message.

Baseline today, measured: 0 evidenced revenue rows in `finance`; M0 not reached;
0 payments through any AION-recorded path.

## Conditions, as numbers

| Condition | Rule |
|---|---|
| **Minimum valid test** | ≥ 30 contacts messaged within the first 3 days, each logged in `contacts.csv` by code (never name or number). Fewer than 30 sent by day 7 means the test did not run; it is BLOCKED on the owner, not failed. |
| **Time window** | 14 days from the first message sent (`sent_at` of row 1). |
| **SUCCESS** | ≥ 3 ACTUAL revenue rows with description prefix `EXP-001` and a Razorpay payment id as evidence, inside the window. (10% paid conversion.) |
| **FAILURE** | ≤ 1 such row when the window closes. |
| **AMBIGUOUS** | Exactly 2 paid at day 14 → extend once: 7 more days, contacts extended to 60. Then ≥ 4 paid total = SUCCESS, else FAILURE. No second extension. |
| **Cost ceiling** | INR 0 advertising. INR 500 total model spend for drafting and tallying (class B, recorded with `aion usage`). Razorpay fees are deducted from revenue, not budgeted. Any request to spend beyond this is an approval card, not a decision. |
| **Owner time ceiling** | 12 hours across the window: ~2.5 h outreach, 2.5 h per paid consult (call + brief), 1 h admin. If the owner cannot give this, say so on day 1 and the experiment does not start. |

## Unit economics (per paid consultation)

| Line | INR | Basis |
|---|---|---|
| Price paid by buyer | 2,499 | inclusive of 18% GST on architectural services |
| GST payable | −381 | 2,499 ÷ 1.18 = 2,118 taxable value |
| Razorpay fee (2% + GST on the fee) | −59 | ESTIMATE from Razorpay's standard published rate; the true figure is on the first settlement |
| **Net cash to the company** | **≈ 2,059** | before the owner's time |
| Owner time | 2.5 h | call 1.5 h, brief 0.75 h, scheduling 0.25 h |
| Model spend | ≤ 20 | drafting the brief skeleton from the call checklist, class B |
| Implied hourly, consult only | ≈ 815 / h | the consult is not the business; the credited-back project is |

The credit-against-project clause means a consult that converts is worth the
project margin, not INR 2,059. That conversion is **not** measured by this
experiment; it is EXP-002's job (see decisions below). This experiment measures
one thing: will anyone pay.

## What is UNKNOWN and the cheapest way to learn it

| Unknown | Cheapest way to learn it | Owner time |
|---|---|---|
| How many warm contacts fit the buyer definition | Owner scrolls WhatsApp and counts; writes the number in `PAYMENT_LINK.md` under `contacts_available` | 10 min |
| Whether the Razorpay account is live-mode and KYC-complete | Owner opens the Razorpay dashboard; live-mode toggle and settlement status are on the first screen | 2 min |
| Whether SevaaConnect has sold a paid consultation before, and at what price | Owner answers one question; if yes, that price replaces 2,499 for this run and the file is amended before the first message | 1 min |
| Who delivers the call (owner or a staff architect) | Owner answers; affects M3 analysis, not this experiment | 1 min |
| Whether a public presence exists (Instagram, website) that contacts will check | Owner answers; if none, the message must not link anywhere, only offer the call | 1 min |
| Razorpay's exact fee on a 2,499 link | Read from the first real settlement | 0 |

Every one of these is a D-class step in the plan (`plan-exp001-paid-consult.json`)
and becomes an approval card on the phone. None of them blocks drafting.

## Measurement

1. The owner logs every message in `contacts.csv` (columns: `contact_code,sent_at,reply,reason_code,paid,payment_ref`). Codes are `C01`…`C60`. Names and numbers never enter this file or git.
2. Every payment is recorded the moment it lands:
   `aion money-add revenue 2499 --stage ACTUAL --description "EXP-001 payer C07" --evidence razorpay:pay_XXXXXXXXXXXXXX`
   The description **must** be `EXP-001 payer <code>` so a second payment from the same code later counts as a repeat payer for M1 (milestones key payers on the description).
3. `aion experiment EXP-001` prints the funnel and the current verdict; the same numbers appear on the phone dashboard and in the `status` reply. `aion experiment EXP-001 --decide` exits 0 only when SUCCESS or FAILURE is reached, so the plan's evaluation step cannot be marked DONE early.
4. M0 is detected by the build loop (`aion milestones --new`) from the finance rows, never claimed by hand. The loop pauses itself when M0 lands.

## The decision each outcome forces

**SUCCESS (≥ 3 paid)**
1. M0 is recorded automatically. The owner is told once, by `status`.
2. Open EXP-002 immediately: convert paid consults into a first project stage (site visit + concept, fixed price, credited fee applied). M1 is a second payment from the same payer code; EXP-002 measures consult→project conversion, which this experiment deliberately does not.
3. Only now authorise T100 (public deployment of the quote funnel), because there is a proven offer to put behind it. `incoming/plan-t100-go-public.json` is applied at this point, not before.
4. No paid traffic until EXP-002 shows at least one consult→project conversion. First ad budget, if ever, is capped at INR 5,000 and is its own approval.

**FAILURE (≤ 1 paid)** — read `reason_code` before choosing:
- If ≥ 5 contacts replied and the most common reason is `price`: run EXP-001b, same offer and channel, price INR 999, 30 new contacts, 14 days. One rerun only.
- If < 5 replied at all, or the top reason is `no_need` or `timing`: the buyer or the offer is wrong, not the price. Do not rerun. Open EXP-003 with a different buyer: small builders and developers in Gujarat, fixed-price 3D visualisation package for one unit. Warm channel again, 14 days.
- In both cases T100 stays closed and no money is spent on traffic.

**AMBIGUOUS (exactly 2)** — extend once as specified above. No other change to price, message or buyer during the extension, or the result is uninterpretable.

**BLOCKED (< 30 sent by day 7)** — not a market result. Record a hands-off gap: the constraint is owner time, which is the M3 wall named in `docs/MILESTONE_LADDER.md`. The next experiment must be one the owner can run in under 3 hours total, or delivery must be delegated first.

## What this experiment does not prove

- That the business can run hands-off (it cannot; the owner delivers the call).
- That the public funnel converts (untested until T100).
- Project margin (EXP-002).

It proves or disproves the single cheapest fact on the path: that a real person
pays real money for a SevaaConnect offer through this machinery.
