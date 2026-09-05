# OWNER README — what is going on, and what only you can do

_Plain words, no jargon. Everything below is also on your phone page (`/app`)
under "Steps to real money", and in the `status` reply as "Needs you: …"._

## Where things stand (measured 2026-09-05)

- Real revenue through the system: **₹0**. Milestone M0 (first real rupee) not reached.
- The software is built and tested (215 tests). The bottleneck is not code.
- The first revenue experiment is designed and its plan is queued. It needs
  **about 4 hours of your time over two weeks** and **₹0 of spend**.

## The real steps to money, in order

| # | Who | What | Time |
|---|---|---|---|
| 1 | system | Experiment EXP-001 designed: a paid "Design Clarity Call" at ₹2,499, sold one-to-one to 30 people you already know. **Done.** | – |
| 2 | cheap model | Writes the WhatsApp message (English + Gujarati), the one-page brief template, and the call checklist. Runs by itself from the plan. | – |
| 3 | **you** | Log in to Razorpay, confirm live mode, create a payment link "Design Clarity Call ₹2,499", paste it and five short answers into `PAYMENT_LINK.md` (copy the template next to it). | 15 min |
| 4 | **you** | Send the message to 30 people, one at a time, over 3 days. Add one row per person to `contacts.csv` using codes C01…C30, never names. | 2 h |
| 5 | **you** | When someone pays: record it the same day with the command below, hold the 90-minute call within 5 days, send the one-page brief within 48 h. | 2.5 h each |
| 6 | system | Computes the verdict from the payments: 3 paid = success, 0–1 = failure, 2 = one extension. You cannot mark it by hand. | – |
| 7 | **you** (only after success) | Open the public funnel (T100): Railway trial, four env vars, privacy mailbox, name a traffic source, three secrets on the PC. | 1 h |
| 8 | system | Repeat payer (M1) via EXP-002, drafted by the cheap model from the verdict. | – |

Record a payment (the only command you must remember; the code is the contact's code):

```bash
aion money-add revenue 2499 --stage ACTUAL --description "EXP-001 payer C07" --evidence razorpay:pay_XXXXXXXXXXXXXX
```

See it all at any time:

```bash
aion path                 # the steps above with live done/next status
aion experiment EXP-001   # the funnel: sent, replied, paid, verdict
aion status               # includes "EXP-001: …" and "Needs you: …"
```

## What the AI does without you

- The **daily cheap loop** (a Sonnet routine, prompt in `deploy/routines/DAILY_CHEAP_LOOP.md`) pulls the branch, runs the tests, executes plan steps that a cheap model can do, appends to `docs/FINDINGS_LOG.md`, commits and pushes. It never sends a message to a real person, never spends money, never touches class-C work.
- The **weekly strong review** (an Opus routine, prompt in `deploy/routines/WEEKLY_STRONG_REVIEW.md`) opens, reads the "needs a strong model" section of the findings log, and **exits immediately if it is empty**. Strong-model spend happens only when something genuinely needs it.
- On the PC, `aion work` runs every 10 minutes under systemd and stops itself the moment M0 lands.

## What never happens automatically

- No outbound message to any real person. You send them.
- No spend, no ads, no subscription, no live payment link creation. Those are approval cards; only `APPROVE <ID>` from your number proceeds.
- No milestone moves on a forecast. Only a payment id moves M0.

## Files you may want to open

- `PROJECTS/sevaa-sales-os/experiments/EXP-001-paid-design-consult/EXPERIMENT.md` — the experiment, one page of numbers.
- `docs/MILESTONE_LADDER.md` — where the real wall is on the way to ₹1,00,000/month (it is M3, hands-off delivery, not M6).
- `docs/SECURITY_REVIEW.md` — what could have gone wrong on the WhatsApp bridge and what was fixed today.
- `docs/FINDINGS_LOG.md` — running log: finding → correction → what is left for the cheap model.
