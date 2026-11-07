# E2E proof obligations
Not “never happened”: these have not been proven by this audit with current code, host and correlated evidence.
Each receipt must include start/end UTC, host, code SHA, canonical task/session IDs, command/exit, expected/actual state, redacted artifact hash and independent verifier.

| Flow | Existing evidence | Missing proof / order |
|---|---|---|
| task -> routing -> execution -> verification -> checkpoint -> result | unit/integration suite, DB DONE rows | one real bounded task, selected executor and independent output evidence (TR-4-03/05) |
| restart -> resume | tests, old checkpoint | controlled restart of one task; no duplicate side effect |
| approval -> exact action | stored openclaw attribution | pending-negative sentence, strict approve once, parameter tamper rejected, repeated delivery idempotent |
| WhatsApp -> canonical task | historical message transcript | fresh marked request/receipt; unmarked chatter no task |
| LucyNest -> canonical task | bridge service running | native socket down; restored display and authorized intake path |
| project -> isolated context/evidence | project field and definitions | two projects; forbidden cross-project lookup/mutation denied |
| backup -> restore | local files, CI tests | encrypted off-host archive restored to isolated home; task/memory counts and integrity |
| update -> smoke -> rollback | deployment docs | deliberately bad candidate rolls back without losing accepted tasks |
| worker/machine loss -> recovery | host-local locks | loss/retry/restart across canonical owner and secondary with no duplicate work |
| TaskCheck -> evidence -> task result | main implementation | owner phone submits real evidence; receipt attributed to correct task |
| useful workflow repeatedly | no current-series evidence | 14-day ledger, actual outcomes, failure count, token/cost per verified success |

Physical touch, Mac hardware, phone-origin messages and service promotion require their respective real environment. Do not substitute shell simulation for those proofs.
