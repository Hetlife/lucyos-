# LucyOS · AION control layer

Personal AI operations hub. The owner steers from WhatsApp on an iPhone; the
Ubuntu PC does the work and holds the truth.

```
WhatsApp    steering wheel      approvals and commands, never secrets
OpenClaw    driver interface    bridges/whatsapp_bridge.py
AION        brain               aion_core/ — state, routing, approvals, resume
agents      workforce           deterministic code, local model, cheap cloud, strong model
Ubuntu PC   permanent office    the canonical shared brain
owner       authority           the only source of Tier-3 approval
```

## Quick start

```bash
scripts/install.sh
aion boot
python3 bridges/whatsapp_bridge.py stdin     # type `status`, `tasks`, `help`
python3 bridges/http_server.py               # private phone UI on 127.0.0.1:8787
```

Full setup, services, backups and recovery: `docs/OPERATIONS.md`.

## What it does

- **Answers the owner without a model.** `status`, `today`, `money`, `tasks`,
  `blockers`, `errors`, `agents`, `approve <ID>`, `deny <ID>`, `pause`, `resume`,
  `safe mode`, `deep check`, `why <ID>`, `report` are regular expressions and
  SQL, so the control channel works when every provider is down.
- **Refuses secrets.** A message containing a credential is refused and never
  stored. Every write to state and every outbound reply is redacted, and
  `aion scan` blocks a commit that carries one.
- **Never calls unfinished work done.** `aion task-done` requires evidence: a
  command that ran, a measurement, an observation.
- **Holds one action, not the system.** A pending approval blocks only its own
  task; everything else keeps running, ranked by expected value.
- **Spends the cheapest thing that works.** Routing goes deterministic code →
  local model → cheap cloud → strong model → owner, and a budget governor moves
  from NORMAL to STOP as a strong-model budget is consumed.
- **Survives being killed.** `aion boot` verifies state, ingests external AI
  packets, applies notebook entries, releases stale claims and names the current
  bottleneck, without blindly repeating the last action.

## Where things are

| Path | What it is |
|---|---|
| `aion` | The CLI entry point |
| `aion_core/` | The control layer — see its README for a module map |
| `bridges/` | Transport adapters and authenticated phone HTTP server |
| `directives/` | The owner's prompt bundle: the authority layer |
| `docs/` | Architecture, WhatsApp commands, operations |
| `scripts/` | Install, services, nightly maintenance, pre-commit |
| `systemd/` | User unit templates for the bridge and the nightly timer |
| `tests/` | 86 tests covering every rule above |
| `<AION_HOME>/` | The shared brain: state, memory, inbox, logs (created, not committed) |

Default `AION_HOME` is `~/openclaw/shared_brain`. It is machine state and is
never committed.

## Two files people edit by hand

Everything in the shared brain is generated except these:

- **`NOTEBOOK.md`** — anyone (owner, ChatGPT, Claude, a local model, OpenClaw)
  appends `[BUG]`, `[TASK]`, `[FACT]`, `[FIX]`, `[NOTE]`, `[QUESTION]` or
  `[HANDOFF]` entries. `aion notebook sync` turns each into real state and stamps
  it so it is never applied twice.
- **`private_state/secrets.env`** — 0600, written only by `aion secrets set`,
  excluded from backups and from git.

## Tests

```bash
python3 -m unittest discover -s tests -t . -q
```

No third-party dependencies. Python 3.9+ and its standard library only.
