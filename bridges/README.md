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

- The webhook checks `X-Bridge-Token` against `WHATSAPP_BRIDGE_TOKEN` and warns
  loudly if the variable is unset. Bind to localhost and front it with a tunnel.
- Message bodies are never written to the HTTP log.
- Replies are redacted and length-capped before they leave.
- A repeated delivery (same message id, or same file name and body) is answered
  once, so a provider retry cannot approve something twice.
- A crash inside the router becomes a logged error and a plain reply, so a bug
  never takes the owner's control channel down.

## Adding a provider

Write a function that gets text and calls `reply_to(message, sender=...)`. That
is the whole contract. Do not import anything else from `aion_core` into a new
adapter.
