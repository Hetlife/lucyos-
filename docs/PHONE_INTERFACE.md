# Phone interface

A mobile-first page at `/app` on the WhatsApp bridge server — the richer
surface for reading state and acting quickly, next to WhatsApp's plain-text
commands. Same backend, same router, same rules: no model call needed to
answer a read, no secret ever leaves the machine, no action taken without an
explicit tap-and-confirm.

## Run it

```bash
aion secrets set PHONE_API_TOKEN      # once, a long random value
python3 bridges/whatsapp_bridge.py webhook --host 127.0.0.1 --port 8765
```

Open `http://<address>:8765/app` on the phone, paste the same token in once —
it stays in that browser's local storage, per-device. Reaching it from
outside the house is a tunnel (Tailscale or `ssh -L`), never an open port;
`--host` still defaults to loopback.

## What it shows, in order

1. **Money first** — real revenue, cost, net, 7-day trend, per project.
   Forecasts render under a separate heading and never touch the real figures.
2. **What changed** — completions with their evidence, money in, failures,
   decisions. Not a log dump.
3. **Needs you** — every pending approval as a card (tap Approve/Deny, then
   confirm — no accidental taps), plus tasks blocked on the owner and tasks
   waiting on a yes/no/later.
4. **Top tasks** — ranked by expected value, same ranking WhatsApp's `tasks`
   uses.

The **+** button captures an idea, a company, a project or a note in a few
seconds. Offline, it queues in local storage and sends when the connection
returns — same triage queue a WhatsApp message lands in.

## API

All `/api/*` GET and POST routes (except `/api/events`, S01's separate
HMAC-signed contract) require `Authorization: Bearer <PHONE_API_TOKEN>`,
checked with `hmac.compare_digest`. Read-only: `/api/status` (or
`/api/dashboard`, same payload), `/api/tasks`, `/api/blockers`, `/api/money`,
`/api/errors`, `/api/agents`, `/api/report`. Actions: `POST /api/command`
`{"message": "..."}` — the exact same router WhatsApp uses, so `APPROVE
A-101` from the phone and from WhatsApp behave identically; `POST
/api/capture` `{"text", "kind"}`; `POST /api/feedback` `{"task_id", "choice",
"note"}`. `/app` itself serves the static page with no auth — it carries no
data, only the shell that then calls the authenticated API.

## Security model

- Bearer token, not a cookie or a login form. No third-party auth.
- Bound to `127.0.0.1` by default; the tunnel is the owner's, documented,
  never an open port.
- Every response passes through `security.redact` (via `aion_core/phone.py`),
  same as every WhatsApp reply.
- A credential-shaped `capture` is refused with the same rule the WhatsApp
  router enforces — checked by a real HTTP round trip in
  `tests/test_bridge.py`, not assumed.
- The page's local-storage cache holds only the dashboard payload (money,
  feed, needs-you, tasks) for offline display with an explicit "as of" time —
  never a raw report or anything the redaction layer would have stripped.
