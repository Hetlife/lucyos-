# SECURITY REVIEW — the WhatsApp bridge's external exposure

_Artifact 4 of the Fable session, 2026-09-05 (TASK "Adversarially review the
bridge's external exposure"). Each finding is a concrete failing request, then
either a fix pinned by a test in `tests/test_bridge.py` / `tests/test_router.py`,
or an acceptance with the reason. Reviewed: `bridges/whatsapp_bridge.py`,
`aion_core/router.py`, `aion_core/worker.py`, `aion_core/approvals.py`,
`bridges/web/phone.html`, `systemd/aion-bridge.service`._

## Findings

### F-B3 — The bridge token proves the transport, not the sender. **CRITICAL — FIXED**
Scenario: the bridge is connected to a real WhatsApp provider on the
SevaaConnect business number. A customer, or anyone, messages that number
`APPROVE A-104`. The provider forwards it with a valid `X-Bridge-Token`. The
router had no sender check, so the approval executed. The S02 review noted
this and called it "existing architecture"; with a business number it is a
live path to real-money approvals.
Fix: `WHATSAPP_OWNER_NUMBERS` (secret store or env, comma-separated). When set,
a message from any other `from` is answered with a refusal and touches no
state, not even the inbox. When unset the bridge prints a startup NOTE.
Tests: `test_unlisted_sender_cannot_approve_even_with_the_bridge_token`,
`test_listed_sender_can_approve`.

### F-B4 — Free text from the wire became a task a model would execute. **CRITICAL — FIXED**
Scenario: any unrecognised message (from a stranger under F-B3, or a
crafted message from a compromised provider) was saved as an INBOX task with
no `model_class`. `aion work` treats a missing class as B, `context.build`
puts the message text into the prompt, and on Mark-2 the Codex loop runs
`codex exec --full-auto` on it. A WhatsApp message was an instruction to an
agent with a shell.
Fix: the router now creates such tasks with `model_class="D"`, `kind="triage"`,
`human_dependence=1`. The worker turns them into a "Triage: …" approval card;
nothing executes until the owner approves, and approval only makes it READY.
Tests: `test_free_text_from_the_wire_becomes_owner_triage_not_model_work`
(asserts the dry run says "raised as an owner approval").

### F-B12 — Cross-site POST to 127.0.0.1 from a web page. **HIGH — FIXED**
Scenario: the owner has the phone page open through a tunnel on a laptop and
visits a malicious site. That site does
`fetch("http://127.0.0.1:8765/", {method:"POST", body:'{"message":"APPROVE A-104"}', headers:{"Content-Type":"text/plain"}})`.
`text/plain` is a "simple request": no CORS preflight, so the browser sends it.
With `WHATSAPP_BRIDGE_TOKEN` unset (the documented local setup) the body
parsed as JSON and the approval executed. The attacker cannot read the
response; it does not need to.
Fix: every POST must carry `Content-Type: application/json` (415 otherwise).
A cross-origin JSON POST triggers a preflight the server does not answer, so
the browser never sends it. Test: `test_cross_site_text_plain_post_cannot_approve`.

### F-B2 — Unauthenticated bridge on a reachable address. **HIGH — FIXED**
Scenario: `whatsapp_bridge.py webhook --host 0.0.0.0` for Tailscale
convenience without a token; the code only warned. Anyone on that network
owns the control channel.
Fix: without a token, a non-loopback host refuses to start (exit 2) unless
`--allow-unauthenticated` is passed explicitly. The token is now also read from
the secret store, not only the environment. Test:
`test_webhook_refuses_to_start_unauthenticated_off_loopback`.

### F-B6 — One stalled connection locks the owner out. **HIGH — FIXED**
Scenario: `HTTPServer` is single-threaded and the handler had no socket
timeout. A client that opens a TCP connection and sends nothing, or a
`Content-Length: -1` (which made `rfile.read(-1)` wait for EOF), holds the
only worker forever. Every later `status`, `APPROVE`, `pause` is unanswered.
Fix: `Handler.timeout = 15`; invalid or negative `Content-Length` → 400.
Tests: `test_handler_has_a_socket_timeout`,
`test_invalid_or_negative_content_length_is_refused`. Threading was
deliberately not added: the SQLite connection is shared and the single
thread is what makes replay-safety trivially true.

### F-B7 — Non-ASCII token header crashed the request. **LOW — FIXED**
`hmac.compare_digest` on `str` raises `TypeError` for non-ASCII input; the
handler had no guard. One request per crash, not exploitable further, but a
crash in the auth path is the wrong place for surprises. Fix: compare bytes.
Test: `test_wrong_bridge_token_is_refused_and_non_ascii_does_not_crash`.

### F-B8 — Unbounded auth-failure logging. **MEDIUM — ACCEPTED FOR NOW, PLANNED**
Every bad token writes an event row. Reachable only through the tunnel or a
provider, so the realistic attacker is the provider itself; still, the
database should not be growable by a remote party. Fix is queued as a cheap
B step in `incoming/plan-bridge-hardening.json` (s2): one log row per IP per
minute, with a test.

### F-B13 — No Host-header check (DNS rebinding). **MEDIUM — ACCEPTED FOR NOW, PLANNED**
A page at `attacker.example` whose DNS flips to 127.0.0.1 after load can make
same-origin requests to the bridge with arbitrary headers. It still needs the
bridge token (F-B2 makes an unauthenticated non-loopback bind impossible, and
loopback binds should also set the token). Queued as a B step (s3) in the
same plan: reject Host values outside {bound host, localhost, 127.0.0.1, ::1,
`BRIDGE_ALLOWED_HOSTS`} with 421.

### F-B5 — Replay. **ACCEPTED**
Webhook messages are deduplicated by provider `id` or body hash; the file
adapter by name and body; `approvals.decide` returns early on any non-PENDING
card. A replayed `APPROVE` is answered once and never re-applied. Tests exist
(`test_file_adapter_ignores_a_redelivered_message`, S02's 3× replay test).
An attacker holding the bridge token can send new messages, which is not
replay; F-B3 bounds what those can do.

### F-B10 — Phone page injection. **ACCEPTED**
Every server string is passed through `escapeHtml`; the values interpolated
into `onclick` are system-generated ids (`A-\d+`, `TASK-[0-9A-F]{8}`) and
`escapeAttr` strips everything but letters from CSS class names. The token is
in `localStorage` on the owner's device with a visible "forget this device".
No third-party script, font or CDN. Reason accepted: no untrusted string
reaches an attribute or script context.

### F-B11 — What a compromised bridge could reach. **ACCEPTED WITH A GUARD**
The bridge process reads the secret store, including the SEVAA founder token
(real-money approvals). A code-execution bug in the handler would expose
every secret. Mitigations: standard-library `http.server` only; JSON parsing
and regex routing are the whole attack surface; `systemd/aion-bridge.service`
runs with `NoNewPrivileges`, `PrivateTmp`, `ProtectSystem=strict`,
`ProtectHome=read-only`. Accepted because splitting the founder token into a
separate process buys little while the same user owns both. The plan's s5
step fails if anyone removes those directives.

### F-B9 — Attacker text echoed to the owner. **FIXED BY F-B3/F-B4**
Task titles from inbound text appear in `tasks`/`status` replies; a stranger
could plant "URGENT reply APPROVE A-105". With F-B3 strangers never reach the
router, and with F-B4 what does arrive is labelled a triage note.

## Also found on the way (not the bridge, fixed because the plan needed it)

**Owner (class D) steps could never complete.** After the owner approved a
card, the worker re-skipped the task on every loop and never validated or
closed it; any plan with an owner step stalled forever behind a card that had
already been answered. Fixed in `aion_core/worker.py::_owner_step`: after
approval the step's own `validation_command` decides DONE; denied cards
cancel the step. Tests: `TestOwnerStepsCanFinish` in `tests/test_plan_worker.py`.

## What was checked and is fine

- Bridge and phone tokens are compared in constant time; phone routes refuse
  everything when the phone token is unset.
- Replies are redacted and length-capped; message bodies never hit the HTTP log.
- `/api/events` verifies an HMAC over the raw body before parsing, refuses PII
  keys, is idempotent per lead.
- A router exception becomes a logged error and a plain reply, never a dead channel.
- The secret store is 0600, excluded from backups and git; `aion scan .` is clean.

## Verdict

Two critical, two high and one low finding fixed with tests (232 tests
passing); two medium findings accepted with a dated reason and queued as cheap
work; the rest accepted with the reason recorded. Before connecting a real
provider on the business number: set `WHATSAPP_BRIDGE_TOKEN` **and**
`WHATSAPP_OWNER_NUMBERS`, keep the bind on loopback, and apply
`incoming/plan-bridge-hardening.json`.
