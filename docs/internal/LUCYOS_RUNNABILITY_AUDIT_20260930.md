> STATUS: HISTORICAL — superseded by `.lucy/planning/lucyos-total-recovery/` (Fable, 2026-09-30). Evidence, not instructions.

# LucyOS — Runnability Audit

**Date:** 2026-09-30 · **Audited:** `origin/main` @ `5d1c6e5` · **Method:** clean clone, real
install, every owner command executed. No claim below is inferred.

---

## Verdict

**LucyOS already runs.** From a clean clone, `scripts/install.sh` completes in about two
minutes, seeds 9 tasks, takes and restore-tests a backup, and reports `healthy`. Every command
in the owner surface works offline at zero cost.

**What is missing is the last mile: the phone.** The bridge cannot reach your actual WhatsApp,
and following `TOMORROW.md` exactly will not get it there — step 5 starts a service that is
guaranteed to fail on a fresh machine. Three specific defects cause that, all small, all
fixable in a day.

So the question "how do we get it running" has a narrower answer than expected: it is running.
Four gaps stand between that and you using it from your phone.

---

## What was proven to work (do not re-test, do not "fix")

Executed on a clean clone at `5d1c6e5` with an isolated `AION_HOME` and `HOME`:

| Step | Result |
|---|---|
| `scripts/install.sh` | exit 0, 65 paths, 8 decisions + 9 tasks seeded, backup made and restore-tested |
| `aion status` | correct — 8 ready, ₹0, next action named |
| `aion tasks` | 8 tasks ranked by expected value |
| `aion milestones` | M0–M6 ladder, all honestly "not reached" |
| `aion boot` | full resume loop, all steps clean |
| `aion fable-ready` | `FABLE READY`, 0 critical blockers, recommends INR 1000 |
| `aion owner-setup` | writes a real batched requirements file |
| `whatsapp_bridge.py stdin` | status / money / tasks / help all answer correctly |
| Full test suite | **745 tests, OK (2 skipped)**, 129s |
| `./aion scan .` | clean |
| `check_portability.py` | 0 violations, 3 known exceptions, 0 stale, 59 files |
| `verify_authority.py anti-dup` | 0 violations |

Health output is honest about its own gaps (`ollama: not installed`, `openclaw: not
configured`) rather than reporting green. That is the design working.

---

## The four gaps

### G-1 (P0) — `aion serve` does not exist

`aion_core/owner_setup.py:21` tells the owner that after setting the bridge token,
"`aion serve` starts answering."

```
$ ./aion --help | grep serve
(nothing)
```

There is no `serve` command. The owner does the setup, runs the command they were told to run,
and gets an error. **This is the first instruction a new owner follows after providing a
credential, and it is wrong.**

Fix: either add `serve` as an alias that launches the bridge adapter, or correct the string to
name the real command. Correcting the string is smaller and should be preferred unless the
owner wants a single front door.

### G-2 (P0) — owner-setup never asks for the credentials the bridge actually needs

`systemd/aion-bridge.service` runs the **`cloud`** adapter:

```
exec /usr/bin/python3 @REPO@/bridges/whatsapp_bridge.py cloud --host 127.0.0.1 --port 8765
```

`bridges/whatsapp_bridge.py:273-281` requires **six** variables and returns exit 2 if any is
empty:

```
WHATSAPP_ACCESS_TOKEN      WHATSAPP_PHONE_NUMBER_ID
WHATSAPP_VERIFY_TOKEN      WHATSAPP_APP_SECRET
WHATSAPP_GRAPH_API_VERSION WHATSAPP_ALLOWED_SENDER
```

`OWNER_SETUP_REQUIRED.md` asks for exactly one secret: `WHATSAPP_BRIDGE_TOKEN` — which the
`cloud` adapter never reads. It belongs to the plain `webhook` adapter, and
`owner_setup.py:128` itself calls it `legacy_bridge_credential_present`, so the entry is
describing a superseded path.

```
$ grep -rn "WHATSAPP_ACCESS_TOKEN" aion_core/
(no matches)
```

**Consequence:** follow `TOMORROW.md` exactly and `aion-bridge.service` exits 2 with
"Missing required environment variables". The owner is never told these exist.

Two of the six are not secrets and should not be treated as such:

- `WHATSAPP_GRAPH_API_VERSION` is a version string (e.g. `v21.0`). It has **no default**, so
  an owner who has supplied every real credential still cannot start the bridge, and nothing
  tells them what value is valid. Giving it a sane default is the smaller, better fix than
  asking the owner for it.
- `WHATSAPP_ALLOWED_SENDER` is the owner's own phone number — a sender allowlist, and a good
  security control. It is configuration, not a credential, and asking for it through
  `aion secrets set` misclassifies it.

This is the single defect most responsible for "LucyOS is not usable from my phone".

### G-3 (P1) — no inbound path from Meta to the machine

The bridge binds `127.0.0.1:8765`. The WhatsApp Cloud API delivers messages by POSTing to a
**public HTTPS URL** with a valid certificate. Loopback cannot receive that.

`docs/OPERATIONS.md:41-44` gives the right guidance for the *web interface* (SSH tunnel, or a
private tunnel such as Tailscale Serve, never bind publicly) but the run path in `TOMORROW.md`
never mentions that the **bridge** needs a public endpoint, and nothing configures one.

Binding the bridge to `0.0.0.0` would be the wrong fix and must not be done. The correct shape
is a named tunnel terminating TLS and forwarding to loopback, with the webhook signature check
(`app_secret`, already implemented at line 229) doing authentication. The security design is
already correct; only the plumbing is absent.

### G-4 (P1) — authority self-drift has reached a constitutional path

```
$ python3 scripts/verify_authority.py self
".github/workflows/lucyos-ci.yml: hash drift",
"aion_core/config.py: hash drift",
"aion_core/db.py: hash drift",
"aion_core/router.py: hash drift",
"aion_core/security.py: hash drift"
"ok": false
```

Five paths now, up from three on 2026-09-24. Two are new: **`security.py`** and — importantly
— **the CI workflow, which is a constitutional path that can never be overridden by a task ID.**

Frozen at `2a70020`; `main` is at `5d1c6e5`. The freeze SHA is legitimately lagging merged
work and `b45f73c` keeps this informational rather than failing CI, so **nothing is broken
today.** But the gap is widening, and a drift list that is always red is a signal nobody reads.
Re-freezing is an owner action and is not in scope for any model.

### Context — branch sprawl kept growing

103 → **124 branches**; 45 → **59 unmerged**. Real progress happened (14 PRs merged in the
31 commits since `81d25a1`, including S-44, S-45, S-48, the Mac resolver and the EAA secret
scanner), but merged branches were not deleted and new ones outpaced the cleanup.

This does not block running LucyOS. It is tracked in `docs/internal/CODE_REVIEW_20260924.md`
F-1 and the handoff package; it stays P1 for repo health and is deliberately **excluded** from
the execution plan below so that getting you onto your phone is not held behind it.

---

## What this means for building and using LucyOS

The mental model to correct: this is not a half-built system that needs finishing. It is a
working system with a disconnected phone cable.

**Today, with no fixes at all**, you can use LucyOS on the PC: `aion status` in the morning,
`aion tasks`, `aion report` in the evening, and `whatsapp_bridge.py stdin` as a local command
surface. That costs nothing and calls no model.

**After G-1 and G-2** (a few hours of work), `aion-bridge.service` starts cleanly and the
system is one tunnel away from your phone.

**After G-3**, WhatsApp becomes the live command and approval surface, which is the point of
the whole design.

**G-4 and branch cleanup** are hygiene. They protect the next six months; they do not gate
this week.

---

## Cost to run

Nothing above requires spending. Ollama is free. The Cloud API is free at the volume one owner
generates. `aion fable-ready` recommends **INR 1000** of initial strong-model credit against a
hard INR 2,000/month ceiling enforced by the budget governor, and the governor downshifts by
itself. No change to that guidance is warranted by this audit.

---

## Execution

Repair tasks are specified in `.lucy/execution/SONNET_GET_LUCY_RUNNING_20260930.md`, written
for a low-token Sonnet session. Owner-only steps are marked and are not delegated.
