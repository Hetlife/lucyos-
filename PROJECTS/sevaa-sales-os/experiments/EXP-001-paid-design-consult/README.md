# EXP-001 folder

| File | Who writes it | What it is |
|---|---|---|
| `EXPERIMENT.md` | strong session (done) | The experiment: hypothesis, numbers, decisions. Read this first. |
| `experiment.json` | strong session (done) | The same rules in machine form. `aion experiment EXP-001` reads it. |
| `contacts.csv` | the owner, one row per message | The funnel log. Codes only (`C01`…), never a name or number. |
| `outreach_message.md` | cheap model (plan step s3) | The exact WhatsApp message, English and Gujarati. |
| `brief_template.md` | cheap model (plan step s4) | The one-page deliverable skeleton. |
| `call_checklist.md` | cheap model (plan step s5) | Questions to ask on the call so the brief writes itself. |
| `PAYMENT_LINK.md` | the owner (plan step s7) | The Razorpay link URL and the answers to the UNKNOWNs. |
| `RESULT.md` | `aion experiment EXP-001 --decide` | Written only when SUCCESS or FAILURE is reached. |

## The CSV, exactly

```
contact_code,sent_at,reply,reason_code,paid,payment_ref
C01,2026-09-08,interested,,1,razorpay:pay_ABC123
C02,2026-09-08,declined,price,0,
C03,2026-09-08,,,0,
```

- `sent_at` ISO date. The first row's date starts the 14-day window.
- `reply` one of: empty (no reply yet), `interested`, `declined`.
- `reason_code` one of: empty, `price`, `timing`, `no_need`, `other`.
- `paid` 0 or 1. A 1 here is a claim; the evidenced count comes from
  `aion money-add ... --evidence razorpay:pay_...` and is what decides.
- `payment_ref` the same `razorpay:pay_...` string, for cross-checking.

## Recording a payment (the only step that moves M0)

```bash
aion money-add revenue 2499 --stage ACTUAL --description "EXP-001 payer C07" --evidence razorpay:pay_XXXXXXXXXXXXXX
aion experiment EXP-001
```
