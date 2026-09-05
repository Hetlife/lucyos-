# bridges/

Transport adapters. The router is pure (text in, text out), so everything that
knows about a network lives here and nowhere else.

`whatsapp_bridge.py` ships three adapters:

| Adapter | Command | Use |
|---|---|---|
| `stdin` | `python3 bridges/whatsapp_bridge.py stdin` | Try commands locally, exactly as the owner would send them |
| `file` | `python3 bridges/whatsapp_bridge.py file` | Any transport that can drop a file: reads `INBOX/whatsapp/*.txt`, writes `OUTBOX/whatsapp/*.reply.txt` |
| `webhook` | `python3 bridges/whatsapp_bridge.py webhook --port 8765` | A provider that POSTs `{"message": "...", "from": "...", "id": "..."}` |

## Security

- The webhook checks `X-Bridge-Token` against `WHATSAPP_BRIDGE_TOKEN` (secret
  store or environment). Without a token it refuses to start on any host but
  loopback unless `--allow-unauthenticated` is passed.
- The token proves the *transport*, not the sender. Set `WHATSAPP_OWNER_NUMBERS`
  (comma-separated, international format) before connecting a business number:
  a message from any other sender is refused before it reaches the router.
- Every POST must be `Content-Type: application/json`; anything else is 415.
  This is what stops a web page from firing a cross-site `text/plain` POST at
  the loopback bridge without a CORS preflight.
- Each request has a 15 s socket timeout and a validated `Content-Length`, so a
  stalled client cannot hold the single-threaded server — and the owner's
  control channel — open forever.
- Unrecognised free text becomes a class-D triage card for the owner, never a
  task a model executes. See `docs/SECURITY_REVIEW.md` for every finding.
- Message bodies are never written to the HTTP log.
- Replies are redacted and length-capped before they leave.
- A repeated delivery (same message id, or same file name and body) is answered
  once, so a provider retry cannot approve something twice.
- A crash inside the router becomes a logged error and a plain reply, so a bug
  never takes the owner's control channel down.

## Phone interface

`web/phone.html` is a self-contained mobile page (no external fonts, scripts
or CDNs) served at `/app` by the `webhook` adapter. It talks to the same
`Handler` class over a set of `/api/*` JSON routes gated by a *separate*
bearer token (`PHONE_API_TOKEN`, not the WhatsApp bridge token) so revoking
one never touches the other. `POST /api/command` routes through
`router.handle` — the exact function WhatsApp uses — so the two surfaces can
never drift into answering the same command differently. See
`docs/PHONE_INTERFACE.md`.

## Adding a provider

Write a function that gets text and calls `reply_to(message, sender=...)`. That
is the whole contract. Do not import anything else from `aion_core` into a new
adapter.
