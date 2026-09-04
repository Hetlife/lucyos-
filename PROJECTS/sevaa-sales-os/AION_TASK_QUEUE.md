# AION TASK QUEUE — SEVAA Sales OS

Priority = impact × confidence ÷ effort, with the F-numbers from the adversarial review. All tasks are **₹0 real spend**, reversible, and executable before the founder opens the T100 gate. Class per the directive: A = high reasoning, B = normal coding, C = low-token, D = no LLM.

## Merge order
`S05 → S01 → S07 → S02 → S09 → S06 → S04`
S05 first so every later branch lands in a self-describing repo. S02 waits for S01 because it reuses the same bridge endpoint pattern and needs the security review that S01's tests establish.

## Branch convention
`agent/<agent-id>/<task-id>-<short-name>` — e.g. `agent/sonnet-1/S01-enquiry-notify`. Claim in `sevaa-sales-os/state/ACTIVE_WORK.json` before the first commit; remove the claim and append a `task_result` to `state/AGENT_EVENTS.jsonl` on completion. Never force-push another agent's branch.

---

### S05 — Pointer files in the SEVAA repo · Class C · IMPLEMENT_NOW
**Why:** F7. Every agent the directive spawns looks for these first.
**Files (create only):** `START_HERE_FOR_AI.md`, `AION_CONSTITUTION.md`, `AION_AGENT_ARCHITECTURE.md`, `AION_STATE.md`, `AION_TASK_QUEUE.md`, `AION_ADVERSARIAL_REVIEW.md`, `MULTI_AGENT_PROTOCOL.md`, `AGENT_TASKS.json`, `MACHINE_HANDOFF.json` at the SEVAA repo root.
**Steps:** each markdown file is ≤ 15 lines: one paragraph saying what it points to, then the path(s). `AGENT_TASKS.json` and `MACHINE_HANDOFF.json` are copies of the files in this folder. Do not paste prose from CURRENT.md or TODO.md; link to them.
**Test:** `python scripts/agent_maintenance.py --check` still OK; `pytest -q` still 36 passed; `git diff --stat` touches only new root files.
**Success:** a new agent given only the repo root can find every authoritative file in one read.
**Failure:** any existing file modified; any duplicated content > 15 lines.

### S01 — Enquiry notification event · Class B · IMPLEMENT_NOW
**Why:** F1, F4. The first real lead must reach the founder within a minute, without PII in chat.
**Allowed files (SEVAA):** `backend/public_enquiry.py`, new `backend/notify.py`, `backend/runtime.py` (settings only), `.env.example`, `tests/test_notify.py`, `docs/spec/API_SPEC.md`.
**Allowed files (AION):** `bridges/whatsapp_bridge.py` (add `POST /api/events`), `aion_core/intake.py` (add `external_event()`), `tests/test_bridge.py`.
**Steps:**
1. SEVAA: add settings `SEVAA_NOTIFY_WEBHOOK_URL` (default empty = disabled) and `SEVAA_NOTIFY_WEBHOOK_SECRET`.
2. `backend/notify.py`: `emit(event: dict)` that POSTs JSON with header `X-Sevaa-Signature: sha256=<hmac>` over the body, 3-second timeout, one retry, never raises into the request path (log and continue). Idempotency key = `enquiry:<lead_id>`.
3. Event payload **only**: `{"type":"enquiry.created","lead_id":…,"score":…,"stage":…,"city":…,"source":…,"requirement_summary":<first 80 chars>,"created_at":…}`. **No name, phone, email, company.**
4. Call `emit` after the insert in `create_public_enquiry` when the URL is set. Honeypot/duplicate paths must not emit.
5. AION: `POST /api/events` on the bridge verifies the HMAC with `SEVAA_NOTIFY_WEBHOOK_SECRET` from the secret store (`hmac.compare_digest`), dedups by `db.seen("sevaa:<idempotency>")`, then `intake.external_event()` creates a `TRIAGE` task titled `Enquiry #<lead_id> score <n> — <city>` and sets an owner alert so the next `status` shows it.
**Tests:** SEVAA — disabled by default emits nothing; enabled emits once per lead with correct signature; duplicate submit does not re-emit; payload contains no `phone`/`email`/`name` keys (assert on the serialized body); webhook failure does not fail the enquiry. AION — bad signature → 401 and nothing stored; valid event → one task, replay → no second task; `status` reply contains the alert.
**Success:** with both sides running locally, a `/quote` submission produces a WhatsApp-style `status` line within one poll.
**Failure:** any PII key in the payload; enquiry request slower than +100 ms p50 with webhook down; more than one task per lead.

### S07 — SEVAA figures inside AION `status`/`today` · Class B · IMPLEMENT_NOW
**Why:** the founder should see enquiries, pending approvals and pipeline in the same `status` they already send.
**Allowed files:** AION `aion_core/reports.py`, new `aion_core/sevaa.py`, `tests/test_sevaa.py`. SEVAA: none.
**Steps:** `aion_core/sevaa.py` wraps `scripts/openclaw_client.py` semantics with the **automation** token only (from secret store `SEVAA_AUTOMATION_TOKEN`, base URL `SEVAA_BASE_URL`): `daily_brief()`, `pending_approvals()`. Cache 60 s. If unreachable, `status` says `SEVAA: unreachable since <time>` — never silently omit. Append one line to `status`: `SEVAA: <n> enquiries today, <m> approvals pending, <k> follow-ups overdue`.
**Tests:** mocked HTTP; unreachable path; token never appears in any reply (assert redact).
**Success:** `aion whatsapp status` shows the SEVAA line against a local SEVAA instance.

### S02 — Founder approvals from WhatsApp · Class B, **Class A security review before merge**
**Why:** F2. Moves the only human-authority action to the phone without weakening it.
**Allowed files:** AION `aion_core/sevaa.py`, `aion_core/approvals.py` (add `external_ref` column via `db._ADDED_COLUMNS`), `aion_core/router.py` (no new commands — reuse `APPROVE/DENY <ID>`), `tests/test_sevaa_approvals.py`. SEVAA: none — the API already exists.
**Steps:**
1. Poll `pending_approvals()` in `resume.boot()`; for each SEVAA approval without an AION card, create one with `external_ref="sevaa:approval:<id>"`, action = proposal title + amount, `why` from the proposal, recommendation `REVIEW`.
2. On `APPROVE A-xxx` for a card with `external_ref`, call `POST /api/v2/approvals/{id}/decision` with the **founder** token read from the secret store at call time, `X-Actor: founder-via-whatsapp`. On `DENY`, send the reject decision. Record the SEVAA response as evidence.
3. Idempotent: a second `APPROVE` must not call SEVAA again (AION already refuses; add a test that proves the HTTP mock is hit once).
4. If SEVAA returns non-2xx, the AION card stays PENDING and `status` shows the error.
**Security review (Class A, before merge):** founder token read only inside the call, never logged, never in a reply; bridge bound to localhost; WhatsApp sender must be the configured owner number; a forged inbound message cannot reach this path without the bridge token. Reviewer writes findings into `AION_ADVERSARIAL_REVIEW.md`.
**Tests:** approve/deny round trip with mocked SEVAA; replay hits HTTP once; non-2xx keeps PENDING; token absent from logs/replies.
**Success:** a pending SEVAA proposal appears as an AION card; `APPROVE` changes its state in SEVAA.

### S09 — Verified payment → AION M0 · Class B · IMPLEMENT_NOW
**Why:** F3. The mission's first milestone must be detected, not claimed.
**Allowed files:** AION `aion_core/sevaa.py`, `aion_core/milestones.py` (no change expected), `tests/test_sevaa.py`. SEVAA: none (`GET /api/v2/revenue` exists).
**Steps:** in the build loop, fetch `/api/v2/revenue` with the automation token; for each verified payment not yet recorded (`db.seen("sevaa:payment:<id>")`), `metrics.record_money("revenue", amount, stage="ACTUAL", project="sevaa-sales-os", evidence="razorpay:<payment_id>")`. Test-mode/sandbox payments (provider flag) are recorded as `stage="SANDBOX"`, never ACTUAL.
**Tests:** one real payment → M0 reached; sandbox payment → M0 not reached; replay → one row.
**Success:** `aion milestones` flips M0 only on a real reconciled payment.

### S06 — Source attribution proven · Class B
**Why:** F6. Without it T104 economics are impossible.
**Allowed files (SEVAA):** `backend/public_enquiry.py`, `web/` quote page, `tests/test_public_enquiry.py`.
**Steps:** `/quote?src=<slug>` → hidden field → `leads.source`; default `public_quote`. Slug whitelist `[a-z0-9_-]{1,32}`; anything else → default.
**Tests:** src persisted; bad src → default; missing → default.

### S04 — Branch hygiene · Class D/C
**Why:** F5. **Steps:** for each remote branch, `git rev-parse <branch>^{tree}` vs the tree of the `main` commit that merged it; delete branches whose content is in `main`; tag `deferred/postgres-path-2026-08-30` on the two Postgres branches then delete them; record the list in `CHANGELOG.md`. **Never** delete a branch with unmerged content that is not deferred by `TODO.md`. **Test:** `git branch -r` lists only `main` plus live agent branches.

---

## Founder actions (the gate — nothing above needs these)
1. Authorise Railway (no-card Trial). 2. Set the four env vars in Railway's secret store. 3. Choose the privacy contact mailbox. 4. Name the first lawful traffic source. 5. On the PC: `aion secrets set SEVAA_AUTOMATION_TOKEN`, `aion secrets set SEVAA_FOUNDER_TOKEN`, `aion secrets set SEVAA_NOTIFY_WEBHOOK_SECRET`.

## Cost strategy
Runtime: ₹0 model spend (verified). Build: S05, S04 on Haiku/deterministic; S01, S07, S09, S06 on Sonnet; S02 on Sonnet with one strong-model security review (~₹150). Record every call with `aion usage`. Governor downshifts automatically.

## By morning (realistic)
S05, S01, S07 merged and green; S09 and S06 green on branches; S02 built and awaiting its security review. The founder's five actions listed and nothing else asked.
