# Master AI Handoff — LucyOS / AION

Updated: 2026-09-04 UTC

## Read this first

You are the lead implementation and planning agent for LucyOS. Verify this
handoff against the live files before acting. Also read:

1. `/root/AGENTS.md`
2. `/root/SESSION_NOTES.md`
3. `/root/openclaw/shared_brain/RESUME.md`
4. `/root/lucyos/README.md`
5. `/root/lucyos/docs/OPERATIONS.md`

Never display, copy, or commit credentials. Do not invent market evidence,
revenue, customers, approvals, or completed validation.

## Repository access and locations

- Active repository: `/root/lucyos`
- GitHub remote: `git@github.com:Hetlife/lucyos-.git`
- Main branch: `main`
- Latest delivered commit at handoff: `03df476` (`Add private AION phone interface`)
- GitHub access works through the existing machine SSH identity. Do not print
  private keys or alter SSH configuration unless explicitly required.
- Other known readable repositories: `/root` notes may reference
  `Hetlife/strategy-factory`, `Hetlife/paperclip`, and `Hetlife/claude-test`.
  They are not in scope unless the owner expands the task.
- Canonical machine state: `/root/openclaw/shared_brain` (not committed to Git).

Before editing, run:

```bash
cd /root/lucyos
git status --short --branch
git log -5 --oneline
```

Preserve unrelated user changes. Use `rg` for searches and `apply_patch` for
file edits. Run the relevant tests before committing.

## Mission and operating boundaries

The mission is to operate and improve LucyOS autonomously toward the first-real-
revenue objective and ultimately INR 1,00,000/month net. Real money and observed
demand only: projections must remain labelled and separate.

- Current required capital is INR 0.
- Do not spend money, publish, message external people, create credentials, or
  expose a service publicly without the appropriate owner authorization.
- Any non-zero experiment cap is Tier-3 and requires an AION approval.
- Keep services bound to loopback unless protected by a private tunnel.
- Never mark an AION task DONE without its stated evidence.

## Verified delivered state

- Commits through `03df476` are pushed to `origin/main`.
- The AION phone interface is implemented in:
  - `/root/lucyos/bridges/http_server.py`
  - `/root/lucyos/web/`
  - `/root/lucyos/systemd/aion-interface.service`
  - `/root/lucyos/tests/test_http_interface.py`
- The interface provides bearer-token authentication, redacted APIs, structured
  approval cards, offline summary caching, offline capture queueing, confirm-before-
  decision controls, and a local-only service definition.
- SQLite connections are thread-local so concurrent HTTP requests are safe.
- Last verification: 140 unit tests passed; JavaScript and shell syntax passed;
  `git diff --check` passed; `aion scan` was clean.
- No interface token was created or exposed, and the interface service was not
  enabled during implementation.

## Current task and blocker

Current task: `TASK-607616E8` — Design and build the AION phone interface.

Status: `NEEDS_REVIEW`. Do not mark it DONE yet. Its remaining acceptance
evidence must come from a physical iPhone:

- Open the interface over a private HTTPS tunnel.
- Confirm live status renders.
- Approve one real pending approval through the page.
- Confirm the approval changes canonical AION state.
- With the PC/interface unreachable, reopen the page and confirm the saved
  snapshot renders with an explicit “as of” time.
- Capture a screenshot as evidence.

## Ordered upcoming plan

### 1. Re-verify the recovery point

Read the files listed above, inspect Git status, and run:

```bash
cd /root/lucyos
./aion context TASK-607616E8
./aion blockers
./aion tasks
```

If live state differs from this handoff, prefer the owner's latest instruction
and verified live state. Record the difference in `/root/SESSION_NOTES.md`.

### 2. Prepare owner-assisted iPhone validation

Ask the owner to perform credential entry locally; never ask them to paste the
token into chat:

```bash
cd /root/lucyos
aion secrets set AION_INTERFACE_TOKEN
scripts/install_services.sh
systemctl --user enable --now aion-interface.service
systemctl --user status aion-interface.service --no-pager
```

Guide the owner to expose `127.0.0.1:8787` through a private HTTPS mechanism
(for example, their private Tailscale network). Do not bind it to a public
address or open a public firewall port.

### 3. Execute and document the acceptance check

Use a real pending approval only if approving it is genuinely intended by the
owner. Never manufacture or approve a consequential action merely for testing.
If no suitable approval exists, validate DENY or defer the real-approval portion
until one naturally exists.

Record exact observations and the screenshot location in the AION task evidence.
If every criterion passes, complete the task with `aion task-done`. If anything
fails, leave it in review, record the failure, fix it with tests, and revalidate.

### 4. Return to first-revenue work

After the phone interface is accepted, inspect the current queue rather than
assuming an ID. The previously identified revenue-design task was
`TASK-12B16CD6`. Its job is to define the first real revenue experiment using
observed demand evidence.

Required experiment content:

- one offer, one buyer type, and one acquisition channel;
- observed demand evidence and clearly stated uncertainties;
- hypothesis and baseline;
- minimum valid test and time window;
- real unit economics and maximum cost;
- success, failure, and stop conditions;
- the decision forced by each outcome;
- a dependency-ordered set of executable work orders.

If reliable demand evidence is absent, perform source-backed research or queue
the missing research capability. Do not fabricate facts or invent an offer.
Any proposed spend or external outreach must follow AION's approval boundary.

### 5. Verification and delivery discipline

For repository changes:

```bash
python3 -m unittest discover -s tests -t . -q
git diff --check
./aion scan
```

Note: HTTP tests require permission to open a temporary loopback socket in some
sandboxed agent environments. A socket permission failure is environmental;
rerun with the allowed local-network permission rather than weakening tests.

Update `/root/SESSION_NOTES.md` after material progress and before every final
response. Maintain `/root/openclaw/shared_brain/RESUME.md` through `aion
checkpoint`. Commit and push completed, tested repository work to `origin/main`
when authorized by the owner's ongoing autonomous-work instruction.

## Exact next action

Re-read live state, then coordinate the owner-assisted private iPhone validation
for `TASK-607616E8`. Do not create or reveal the interface token yourself. Once
the physical acceptance evidence is recorded, complete that task and proceed to
the highest-value verified revenue-experiment task in the live queue.
