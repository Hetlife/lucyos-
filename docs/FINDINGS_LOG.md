# FINDINGS LOG — finding → correction → what is left for the cheap model

_Append-only. Every session (strong or cheap, human or routine) adds rows at
the bottom of the first table and, only when something genuinely cannot be
done by a cheap model, one row to the second table. The weekly strong-model
routine reads the second table first and exits immediately if it is empty.
That is the whole cost-control loop: cheap by default, strong only on demand._

## Findings and corrections

| Date | Who | Finding | Correction made | Left for the cheap model | Status |
|---|---|---|---|---|---|
| 2026-09-05 | Fable (strong) | No revenue experiment existed; T100 was being treated as the next step although it has no traffic source and no proven offer | EXP-001 written: paid ₹2,499 consultation to 30 warm contacts, verdict by code; money path puts T100 at step 7, after success | Run `incoming/plan-exp001-paid-consult.json` (s3, s4, s5, s12 are B steps) | plan applied |
| 2026-09-05 | Fable (strong) | A message from any WhatsApp sender the transport forwards could approve real actions (bridge token proves transport only) | `WHATSAPP_OWNER_NUMBERS` allowlist in the bridge; strangers refused before the router | Add it to owner setup and OPERATIONS (plan-bridge-hardening s4) | fixed, tested |
| 2026-09-05 | Fable (strong) | Unrecognised inbound text became a class-B task the autonomous loop would hand to a model with a shell | Router creates class-D triage tasks; worker raises a "Triage:" card instead of executing | none | fixed, tested |
| 2026-09-05 | Fable (strong) | Cross-site `text/plain` POST from a web page could reach the loopback bridge without a preflight | All POSTs require `Content-Type: application/json` (415 otherwise) | none | fixed, tested |
| 2026-09-05 | Fable (strong) | Unauthenticated bridge could be started on a non-loopback host with only a warning | Refuses to start without a token off loopback unless `--allow-unauthenticated` | none | fixed, tested |
| 2026-09-05 | Fable (strong) | One stalled client or a negative Content-Length blocked the single-threaded server forever | Socket timeout 15 s; invalid/negative length → 400 | none | fixed, tested |
| 2026-09-05 | Fable (strong) | Owner (class-D) plan steps could never complete after approval, so every plan with an owner step would stall | Worker validates and closes D steps after approval; denied cards cancel | none | fixed, tested |
| 2026-09-05 | Fable (strong) | The owner had no single place showing what only they must do to make money | `aion path`, `PROJECTS/<project>/money_path.json`, phone "Steps to real money" card, `status` "Needs you" line, `OWNER_README.md` | Keep `money_path.json` current when a plan adds a step | built, tested |
| 2026-09-05 | Fable (strong) | Experiment verdicts would have been judged by hand | `aion experiment <ID> --decide` computes SUCCESS/FAILURE/EXTENDED/BLOCKED from ACTUAL revenue rows and the funnel log | Fill `contacts.csv` rows only from the owner's log; never invent rows | built, tested |
| 2026-09-05 | Fable (strong) | Auth failures log one event row each, unbounded | none yet | plan-bridge-hardening s2 (B): one row per IP per minute, with test | accepted, planned |
| 2026-09-05 | Fable (strong) | No Host-header check (DNS rebinding) | none yet | plan-bridge-hardening s3 (B): 421 for foreign Host, with test | accepted, planned |
| 2026-09-05 | Fable (strong) | `main` and the working branch diverged: main carries an earlier, parallel phone interface (`web/`, `bridges/http_server.py`) that the branch superseded | none — owner decision | none; a strong session or the owner should decide whether main is reset to this branch or the two are merged (only `README.md` and `scripts/install_services.sh` conflict) | needs owner |
| 2026-09-05 | Fable (strong) | The loop retried a failing task three times inside one run (it stays the top READY row), burning every retry in seconds and blocking it before anything else ran | Worker tries each task at most once per run | none | fixed, tested |
| 2026-09-05 | Fable (strong) | A fresh `aion seed` re-queued five class-C jobs that are already done in the repo (experiment, decomposition, phone interface, ladder, security review) and three DET tasks with no command that could only fail | Seed marks work DONE when its artifact exists in the repository (`done_when` glob); owner-only tasks are class D with a validation the loop can run | none | fixed, tested |

## Needs a strong model (weekly review reads this first; empty = exit)

| Date | Raised by | What | Why a cheap model cannot do it | Status |
|---|---|---|---|---|
| 2026-09-05 | Fable | Decide the branch strategy: reset `main` to the Fable branch, or merge main's parallel phone interface into it | It is a product decision with two conflicting implementations; the owner or a strong session must choose which survives | open |
