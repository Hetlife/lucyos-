> STATUS: HISTORICAL — superseded by `.lucy/planning/lucyos-total-recovery/` (Fable, 2026-09-30). Evidence, not instructions.

# Sonnet follow-ups after R-01..R-04 — 2026-09-30

> **STATUS: COMPLETE and HISTORICAL (2026-09-30).** Every task in this file was done and merged.
> The current state and what remains is in `.lucy/execution/SONNET_MASTER_PLAN_20260930.md`
> (see its "Current status" section). Do not treat the base SHA, test counts or PR states below as current.

**Depends on:** PRs #75 → #76 → #77 → #78 (stacked; merge in that order). These tasks assume
that stack is merged, or stack their branches on `task/R-04-bridge-start-proof`.
**Owner decisions recorded 2026-09-30:** (1) **OpenClaw is the primary WhatsApp channel.**
(2) Plan the `set_secret` quoting fix as its own task. (3) R-05 stays parked.

Same rules as `SONNET_GET_LUCY_RUNNING_20260930.md`: never weaken a test, never invent a task
ID, never edit `.lucy/authority/**` / `verify_authority.py` / the CI workflow, never merge,
one task per branch, no new dependency, no new `aion_core` module, never print a secret value.

---

## Why R-06 exists (evidence, not assumption)

`integrations/openclaw/lucyos/SKILL.md` says it plainly: *"LucyOS is the control plane.
OpenClaw is the conversation/channel and execution surface."* OpenClaw reaches LucyOS through
`lucyosctl`. `docs/LUCYOS_OPENCLAW_INTEGRATION_EXECUTION_PLAN.md` (baseline dated 2026-09-17,
so **historical until reverified**) records WhatsApp as intentionally unconnected, waiting for
the owner to connect it inside OpenClaw.

So for this owner the direct Meta Cloud API bridge (`aion-bridge.service`) is a *secondary*
path, not the main one — but R-02 made it a `REQUIRED NOW` item, and `TOMORROW.md` step 5
tells the owner to start it unconditionally. With no Meta variables set, that service exits 2
and `Restart=always` relaunches it every 5 seconds: **an OpenClaw-only owner following
TOMORROW.md ends up with a service crash-looping forever.**

---

## R-06 (P0 for this owner) — stop presenting the direct Meta bridge as required

**Files:** `aion_core/owner_setup.py`, `TOMORROW.md`, `docs/OPERATIONS.md`,
`tests/test_owner_setup.py`

1. `owner_setup.py`: move the "WhatsApp Cloud API bridge (aion-bridge.service)" requirement
   from `REQUIRED NOW` to `OPTIONAL LATER`. Reword `purpose` so it says: only if you also want
   a direct Meta channel alongside OpenClaw. Keep `secret`, `action`, `satisfied` and the
   drift-test coupling exactly as they are — the coupling is the point of R-02.
2. `TOMORROW.md` step 5: make `systemctl --user enable --now aion-bridge.service`
   conditional ("only if you use the direct WhatsApp Cloud API bridge; OpenClaw owners skip
   this"). Do the same for the six `aion secrets set WHATSAPP_*` lines added in R-02.
3. `docs/OPERATIONS.md`: add one sentence at the top of the "WhatsApp Cloud API bridge"
   section saying OpenClaw owners do not need it.
4. Test: with `openclaw_present=True` and every `WHATSAPP_*` variable missing, `render()` must
   contain **no** `REQUIRED NOW` heading for the Cloud bridge, and must still list it under
   `OPTIONAL LATER`. Do not weaken any existing assertion.

**Do not** change `systemd/aion-bridge.service`, `Restart=always`, or the installer here; that
is a separate ruling (see "Flag, do not fix").

**Verify from the repo only.** Do not assert how OpenClaw links WhatsApp — that procedure is
not in this repo and must not be invented. If the owner-setup text needs an OpenClaw step,
write "connect WhatsApp inside OpenClaw" and point at `aion openclaw-check`
(`bridges/openclaw_check.py`) for the gateway probe.

**Done when:** the new test passes, the existing suite is unchanged apart from that,
`check_portability.py` clean, `strict` OK.

**Flag, do not fix (owner rulings):**
- `aion_core/seed.py:178` — the seeded task "Connect the WhatsApp bridge to the real
  transport" still says `aion secrets set WHATSAPP_BRIDGE_TOKEN, then start
  aion-bridge.service`. Wrong for an OpenClaw-primary owner; affects only newly seeded DBs.
- `systemd/aion-bridge.service` restarting every 5 s when its variables are missing. A
  bounded restart policy would be safer; that is a service-design change.

---

## R-07 (P1) — quote secrets on write so the shell loader reads them back exactly

**Problem (verified by execution, PR #78):** `bootstrap.set_secret` writes `NAME=value`
unquoted; the service loads the file with a shell `source`. Space or `&` → value dropped;
`pa$word` → `pa`; `;` → the rest is executed as a command. Meta-issued tokens are URL-safe
and unaffected; owner-invented values are not.

**Why this is not a one-line fix — the complete reader inventory (measured on `origin/main`):**

| Loader | Where |
|---|---|
| Writer | `aion_core/bootstrap.py` `set_secret` |
| Python readers | `bootstrap.py` `has_secret`; `cli.py` (`secrets list`); `health.py`; `model_gateway.py` `_secret`; `sevaa.py`; `bridges/http_server.py`; `backup.py` |
| Shell loaders | `systemd/aion-bridge.service`; `deploy/launchd/com.lucyos.aion-bridge.plist` |

Changing the write format without changing every Python reader breaks them all at once.

**Design (smallest that is correct):**
1. Write `NAME='value'`, escaping an embedded single quote as `'\\''`. That is valid shell and
   loads back byte-exact.
2. Add **one** parser in `aion_core/bootstrap.py` (existing module — no new module; `anti-dup`
   forbids one) that accepts **both** the new single-quoted form **and** legacy unquoted
   lines. Route every Python reader listed above through it. Legacy files must keep working.
3. `has_secret`: `NAME=''` is empty, not set.
4. Do not migrate existing values automatically. A legacy value that is broken for the shell
   stays broken; `scripts/bridge_preflight.py` already reports that by name.

**Tests (all required):**
- Round-trip: for values containing space, `&`, `$`, `;`, `#`, backtick, `"`, `'`, `\\`,
  newline-free unicode — `set_secret` then (a) the Python parser and (b) a real
  `bash -c 'set -a; . file; set +a'` both return the original bytes.
- A legacy unquoted file is still read correctly by every Python reader.
- No reader logs or prints a value.
- Existing `has_secret` semantics unchanged for non-empty values.

**Stop and ask** if: any reader turns out to parse the file differently from the inventory;
a fix appears to need a new module; or a value with a newline must be supported (the file is
line-oriented; refuse newlines with a clear error rather than guessing).

**Done when:** round-trip tests pass for both loaders, all readers migrated, full suite and
gates green, and `prove_bridge_start.py` still passes with a value containing a space.

---

## R-05 stays parked

`.gitignore` is a protected path with no ratified override. Owner assigns a task ID first.
