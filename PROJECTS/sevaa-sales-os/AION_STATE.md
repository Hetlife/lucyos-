# AION STATE — SEVAA Sales OS

Measured 2026-09-03 from a fresh clone of `het-life/sevaaconnect-realestate` at `main` = `a85a8cc` (2026-08-30). Nothing below is inferred from documentation alone.

## Verified facts

| Fact | Evidence |
|---|---|
| 36 tests pass | `pytest -q` → `36 passed in 1.51s` |
| Agent control plane consistent | `agent_maintenance.py --check` → `OK: 10 agents` |
| Runtime makes **zero** paid model calls | grep for openai/anthropic/claude/gpt/ollama/llm in `backend/` and `scripts/`: no source hits |
| No secrets in source | AION scanner: only test fixtures (Bearer tokens in tests) and a localStorage key name in the console |
| Backend is small | 981 lines across the four core modules; 3,303 lines including scripts |
| 36 API routes | founder/automation split, public `/quote` + `/privacy`, Razorpay webhook, proposal shares |
| `main` is 4 days stale | last commit 2026-08-30; 12 remote branches, 10 with commits not in `main` |

## Economic reality (the only numbers that matter)

| Metric | Value | Stage |
|---|---|---|
| Verified external enquiries | **0** | real |
| Verified paid pilots | **0** | real |
| Verified collected cash | **₹0** | real |
| Modeled customers for ₹1,00,000/month | 13 at ₹14,999/month ex-GST | **paper** |
| Software evidence level | 5 — paper/sandbox/shadow | — |

## Where the system actually is

All repository engineering that can precede public deployment is done and tested: ingestion, scoring, pipeline, founder-gated approvals, proposal artifacts, secure shares, Razorpay adapter (credentials outside Git), privacy notice with server-enforced acknowledgement, rate limits, migrations, backup/restore, Docker, a six-check non-mutating deployment verifier, and a 10-role agent control plane.

## The gate

**T100 — public HTTPS deployment** is `BLOCKED_EXTERNAL`. Only the founder can:

1. Authorise a Railway account/project (no-card Trial first; paid Hobby is a separate approval)
2. Set `SEVAA_FOUNDER_TOKEN`, `SEVAA_AUTOMATION_TOKEN`, `SEVAA_ALLOW_LEGACY_V1=0`, `SEVAA_DB_PATH=/data/sevaa.db` in the host secret store
3. Choose a monitored `SEVAA_PUBLIC_CONTACT_EMAIL`
4. Name the first lawful traffic source

Until then, T101–T104 are blocked behind it. Everything else in the SEVAA queue (T200+, T300) is deliberately deferred.

## What AION adds that SEVAA lacks

SEVAA has a founder console. It does **not** have: a way to tell the founder an enquiry arrived, a way for the founder to approve from a phone, a budget governor, a milestone detector, or an autonomous worker loop. AION has all five, tested. The plan connects them.

## Mode

`external_host_authorization_blocked` — correct. The autonomous work below is everything valuable that does **not** need the gate to open.
