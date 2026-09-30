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

## R-02 (P0) — make owner-setup request what the bridge actually needs

**Files:** `aion_core/owner_setup.py` (+ its test), possibly `bridges/whatsapp_bridge.py`

`systemd/aion-bridge.service` runs the `cloud` adapter. `bridges/whatsapp_bridge.py:273-281`
requires **six** variables and returns exit 2 if any is empty:

```
WHATSAPP_ACCESS_TOKEN      WHATSAPP_PHONE_NUMBER_ID
WHATSAPP_VERIFY_TOKEN      WHATSAPP_APP_SECRET
WHATSAPP_GRAPH_API_VERSION WHATSAPP_ALLOWED_SENDER
```

Owner-setup asks for one: `WHATSAPP_BRIDGE_TOKEN`, which `run_cloud` never reads.
`owner_setup.py:128` already calls it `legacy_bridge_credential_present`.

**Classify the six before writing anything — they are not all secrets:**

| Variable | Kind | Handling |
|---|---|---|
| `WHATSAPP_ACCESS_TOKEN` | secret | `aion secrets set` |
| `WHATSAPP_APP_SECRET` | secret | `aion secrets set` |
| `WHATSAPP_VERIFY_TOKEN` | secret (owner-chosen) | `aion secrets set`; say it is a value the owner invents and pastes into the Meta console |
| `WHATSAPP_PHONE_NUMBER_ID` | identifier | from the Meta console |
| `WHATSAPP_ALLOWED_SENDER` | config — owner's own number | a sender allowlist, not a credential |
| `WHATSAPP_GRAPH_API_VERSION` | config — e.g. `v21.0` | **give it a default in `run_cloud`** |

`WHATSAPP_GRAPH_API_VERSION` having no default is its own defect: an owner can supply every
real credential and still be blocked by a version string nobody told them. **Prefer adding a
sane default in `run_cloud` over asking the owner for it** — that removes a required field
instead of documenting one. If you add a default, add a test pinning it.

**Do:** replace the stale WhatsApp entry in REQUIRED NOW with entries covering what genuinely
still needs the owner, using the existing `dict(...)` shape in `REQUIREMENTS` (tier / service /
secret / purpose / permission / action / security / revoke / resumes / satisfied /
satisfied_detail). Update the `satisfied` lambda so it measures the variables the cloud
adapter actually reads, not `legacy_bridge_credential_present`. Keep the
"never send a secret through WhatsApp" rule.

Keep `WHATSAPP_BRIDGE_TOKEN` only if the plain `webhook` adapter is still supported. If you
cannot establish that from the code, ask — do not delete it on a guess.

**Never** read, print or log a secret value. Build test fixtures from obviously fake values
assembled at runtime so `./aion scan .` cannot trip.

**Test — this is the real deliverable.** Derive the required-variable set *from*
`bridges/whatsapp_bridge.py` (the `names` tuple in `run_cloud`) and assert owner-setup covers
every entry that still needs the owner. Do not duplicate the list into the test. A hard-coded
list lets this exact bug come back the next time the adapter changes; the coupling is what
makes the fix permanent.

**Done when:** a fresh `aion owner-setup` accounts for every variable `run_cloud` requires;
the drift test passes; `./aion scan .` clean; 745+ tests OK.

## R-03 (P1) — document and script the inbound tunnel

**Files:** `docs/OPERATIONS.md` (+ a preflight script under `scripts/` if it earns its place)

Meta delivers webhooks to a public HTTPS URL. The bridge binds `127.0.0.1:8765`. Nothing in
the run path bridges that, so even with R-02 done, no message arrives.

**The security design is already correct — do not touch it.** `CloudHandler` at
`bridges/whatsapp_bridge.py:190-235` already implements both halves properly:

- `do_GET` — Meta's verification handshake: requires `hub.mode=subscribe`, compares
  `hub.verify_token` with `hmac.compare_digest`, echoes `hub.challenge`, else 403.
- `do_POST` — verifies `X-Hub-Signature-256` as `sha256=HMAC-SHA256(app_secret, raw_body)`
  with `hmac.compare_digest`, rejects with 401 and logs `whatsapp.signature_failed` via
  `db.log_event`. Also caps body size at `MAX_MESSAGE_BYTES * 16` → 413.

So the only thing missing is TLS termination and forwarding. Write that down; do not rebuild
authentication that already exists.

**Do:** add a concrete section to `docs/OPERATIONS.md` covering: terminating TLS at a named
tunnel and forwarding to `127.0.0.1:8765`; the exact callback URL and verify-token to paste
into the Meta console; how to confirm the `GET` handshake returned the challenge; and how to
confirm the first `POST` passed the signature check (the `whatsapp.signature_failed` event
*not* appearing, plus a successful reply).

State explicitly that the bridge stays on loopback and that binding `0.0.0.0` is never the
fix. Match the loopback-plus-private-tunnel posture already in this file at lines 41-44 for
the web interface — do not invent a second, different posture.

**Only add a script if it does something a reader cannot trivially do by hand.** A wrapper
around a tunnel binary is not worth a file. A preflight that checks the six variables are
present, the port is listening, and the handshake path answers **is** worth it.

**Do not** sign up for any tunnel provider, create any account, or spend anything. Document
the options; the owner chooses.

**Done when:** a reader following only this section reaches a verified webhook; no new
dependency; gates clean.

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

## R-05 (P2, OWNER-GATED — do not start without an assigned task ID)

**File:** `.gitignore`

`scripts/check_boundaries.py` writes `evidence/boundary_report.md` whenever the test suite
runs (`tests/test_check_boundaries.py:21` reads it back). That path is untracked and absent
from `origin/main`, so **every contributor who runs the tests gets a dirty working tree** and
may commit the artifact by accident.

The fix is one line in `.gitignore`. **But `.gitignore` is a protected path** in
`HIGH_MODEL_BASELINE.json` — protected, not constitutional, so an override *is* possible, but
it does not exist yet and `verify_authority.py strict` will refuse the change without one.

**Do not invent a task ID to get past the gate.** Adding the override means editing
`.lucy/authority/**`, which is constitutional and refused unconditionally — only the owner can
land that. If an override for this work has been ratified by the time you read this, apply the
one-line change and reference that ID in the commit trailer. Otherwise leave it and say so in
your report.

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
