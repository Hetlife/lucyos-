# Sonnet Execution Plan — get LucyOS onto the owner's phone

**Base:** `origin/main` @ `5d1c6e5` · **Evidence:** `docs/internal/LUCYOS_RUNNABILITY_AUDIT_20260930.md`
**Written for:** a low-token Sonnet session. Four tasks. One branch and one PR each.

---

## Read before starting (and nothing else)

The audit already proved the following at `5d1c6e5`. **Do not re-verify these, do not re-test
them, do not "improve" them.** Re-running them is the main way this plan wastes tokens.

- `scripts/install.sh` works from a clean clone. 745 tests pass (2 skipped). `./aion scan .`
  clean. `check_portability.py` 0 violations / 0 stale. `anti-dup` 0 violations.
- `aion status | tasks | milestones | boot | fable-ready | owner-setup` all work.
- `whatsapp_bridge.py stdin` works.
- `verify_authority.py self` reports 5 hash drifts. That is **known, informational, and owner
  business**. Do not attempt to fix it and do not re-freeze.

**Out of scope for this plan entirely:** branch cleanup, the 124/59 branch counts, readability
reformatting, access logging, module growth. Those are tracked elsewhere. Touching them here
will block the phone work behind repo hygiene, which is the opposite of the goal.

## Rules

1. Never weaken or skip a test to get green. Never edit `scripts/verify_authority.py`,
   `.github/workflows/lucyos-ci.yml`, or anything under `.lucy/authority/`.
2. Never push to `main`. Never force-push. Never merge. Open the PR and stop.
3. One task per branch, one task ID per PR, so `verify_authority.py strict` can pass.
4. Do not add a third-party dependency. LucyOS core is Python standard library only.
5. Do not create a new `aion_core` module. `anti-dup` will catch it and it is finding F-4.
6. Never bind the bridge to `0.0.0.0`. Loopback plus a tunnel is the design.
7. If a gate blocks you, the gate wins — report it, do not route around it.
8. Report honestly. If a step did not run, say so.

---

## R-01 (P0) — fix the `aion serve` instruction

**File:** `aion_core/owner_setup.py:21`

The `resumes=` string tells the owner "`aion serve` starts answering." No such command exists.
The owner hits this immediately after providing their first credential.

**Do:** change the string to name the command that actually starts the bridge, matching what
`systemd/aion-bridge.service` runs. Do **not** invent a new `serve` CLI command — that is a
larger change, it needs owner sign-off on the front-door design, and the smaller fix removes
the defect completely.

**Test:** add an assertion to the existing owner-setup test that the generated
`OWNER_SETUP_REQUIRED.md` contains no reference to a command absent from the CLI parser.
Derive the command list from the parser, not from a hard-coded list, so the test keeps working
as commands change.

**Done when:** test passes; `aion owner-setup` output names only real commands; 745+ tests OK.

---

## R-02 (P0) — make owner-setup request the credentials the bridge actually needs

**Files:** `aion_core/owner_setup.py` (+ its test)

`systemd/aion-bridge.service` runs the `cloud` adapter. `bridges/whatsapp_bridge.py:274`
requires all four of:

```
WHATSAPP_ACCESS_TOKEN  WHATSAPP_PHONE_NUMBER_ID  WHATSAPP_VERIFY_TOKEN  WHATSAPP_APP_SECRET
```

and exits if any is missing. Owner-setup currently asks only for `WHATSAPP_BRIDGE_TOKEN`,
which the `cloud` adapter never reads.

**Do:** replace the single WhatsApp entry in the REQUIRED NOW section with one that requests
all four, each keeping the existing entry shape (purpose / minimum permission / exact owner
action / security impact / revocation / what resumes afterwards). Keep the
"never send a secret through WhatsApp" rule and the `aion secrets set <NAME>` form. State
plainly in the entry that the four come from the Meta WhatsApp Cloud API app console.

Keep `WHATSAPP_BRIDGE_TOKEN` as a separate entry only if the plain `webhook` adapter is still
a supported path; if you cannot establish that from the code, ask rather than guess.

**Do not** read, print, or log any secret value. **Do not** hard-code a token anywhere,
including in tests — build test fixtures from obviously fake values assembled at runtime so
`./aion scan .` cannot trip.

**Test:** assert the generated file requests exactly the variable names the `cloud` adapter
requires. Derive that set from `bridges/whatsapp_bridge.py` rather than duplicating the list,
so the two can never drift apart again. **That coupling is the real deliverable of this task**
— the literal list is the smaller half.

**Done when:** a fresh `aion owner-setup` asks for every variable the service needs; the drift
test passes; `./aion scan .` clean; 745+ tests OK.

---

## R-03 (P1) — document and script the inbound tunnel

**Files:** `docs/OPERATIONS.md` (+ a script under `scripts/` if it earns its place)

Meta delivers webhooks to a public HTTPS URL. The bridge binds `127.0.0.1:8765`. Nothing in
the run path bridges that, so even with R-02 done, no message arrives.

**Do:** add a short, concrete section to `docs/OPERATIONS.md` covering: terminating TLS at a
named tunnel and forwarding to `127.0.0.1:8765`; the exact callback URL and verify-token
values to paste into the Meta console; how to confirm the `GET` verification handshake
succeeded; and how to confirm the first inbound `POST` was signature-checked by the existing
`app_secret` path at `whatsapp_bridge.py:229`.

State explicitly that the bridge stays on loopback and that binding `0.0.0.0` is never the fix.
Match the existing loopback-plus-private-tunnel guidance already in this file for the web
interface — do not invent a second, different posture.

**Only add a script if it does something a reader cannot trivially do by hand.** A wrapper that
just calls a tunnel binary is not worth a file. A preflight that checks the four variables are
present, the port is listening, and the signature path is reachable **is** worth it.

**Do not** sign up for any tunnel provider, create any account, or spend anything. Document the
choice; the owner makes it.

**Done when:** a reader following only this section gets a verified webhook; no new dependency;
gates clean.

---

## R-04 (P1) — end-to-end proof on a clean clone

**File:** new test or script under `tests/` or `scripts/`, plus evidence recorded via
`aion checkpoint`.

**Do:** prove, in one runnable artifact, that a clean clone reaches a state where
`aion-bridge.service` would start — that is, install succeeds, the four variables being absent
produces a *clear, named* error rather than a silent failure, and with fixture values present
the cloud adapter initialises and binds loopback.

Do not contact Meta. Do not send a real message. Stop at "the process starts and is listening",
which is the honest boundary of what can be proven without the owner's credentials.

**Record what remains unproven.** The audit's `TOMORROW.md` §"What is not proven yet" is the
right standard: the bridge has still never sent a message to a real phone, and this task does
not change that. Say so in the evidence rather than implying end-to-end success.

**Done when:** the artifact runs green from a clean clone; evidence checkpointed; the
unproven-remainder is written down.

---

## Owner-only — not for any model

- Providing the four WhatsApp Cloud API credentials on the PC via `aion secrets set`.
- Choosing and paying for a tunnel provider, if the chosen one costs anything.
- Adding INR 1000 strong-model credit (`aion fable-ready` recommends it; ceiling INR 2,000/mo).
- Re-freezing authority hashes to clear the five-path drift, including the CI workflow.
- Merging any PR from this plan.

## Order and stopping

R-01 → R-02 → R-03 → R-04. R-01 and R-02 are both small and both P0; do them first even if
R-03 looks more interesting.

Stop and ask rather than guessing if: `WHATSAPP_BRIDGE_TOKEN`'s role is unclear; a fix appears
to need a new `aion_core` module; or a gate fails for a reason not covered above.

## Final report

1. Each task: branch, PR link, what you ran, actual output.
2. Test count before and after. It must not drop.
3. What you did not do, and why.
4. Anything in the audit that turned out to be wrong — the repository wins over the audit.
