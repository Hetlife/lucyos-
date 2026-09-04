# AION — master briefing and gap study

One document a strong-reasoning session (or anyone) can read to get the full
picture: what the system is, exactly what is built vs. missing, and the real
path to money. Everything below is measured against the repository and the
running system as of 2026-09-04, not aspirational.

---

## 1. What this is

LucyOS is a personal, always-on business partner, not a productivity tool.
The owner brings ideas; LucyOS carries them through evidence, testing and
execution — proposing, building, measuring, and telling the owner honestly
when an idea is failing rather than looking busy. It runs permanently on one
Linux server; the owner steers it from a phone. Three layers:

```
WhatsApp / phone app   ->  owner sends commands and approvals, never secrets
AION (aion_core/)      ->  the brain: state, tasks, budget, approvals, memory
workers                ->  deterministic code -> local model -> cheap cloud -> Fable
```

Mission: **INR 1,00,000/month of real, owner-withdrawable net profit**, tracked
by milestones M0–M6 that move only on actual revenue rows (`finance` table,
`stage='ACTUAL'`). Forecasts and simulations are recorded but never move a
milestone — this is enforced in code (`aion_core/milestones.py`), not policy.

## 2. Structure — every module and what it owns

| Module | Owns |
|---|---|
| `router.py` | Deterministic WhatsApp/phone commands — regex + SQL, no model call |
| `tasks.py` | The global task queue: states, ownership, expected-value ranking |
| `approvals.py` | Tier-3 approvals — only literal `APPROVE <ID>` / `DENY <ID>` decides |
| `governor.py` | Budget states NORMAL → SHIFT-DOWN → RESERVE → CRITICAL-ONLY → STOP |
| `fable.py` | The strong-model budget, phases, readiness measurement |
| `agents.py` | Model routing (DET/A/B/C/D) with evidence-based escalation |
| `milestones.py` | M0–M6, computed only from real finance rows |
| `security.py` | Redaction, secret-shaped-content refusal, the pre-commit scanner |
| `db.py` | SQLite, additive-only migrations — never drops or renames a column |
| `phone.py` | The phone API backend — see §5 |
| `sevaa.py` | The template for connecting a revenue module: signed webhooks, allow/forbidden field lists |
| `resume.py` | Boot/recovery — verifies state, never blindly repeats the last action |
| `worker.py` | Executes validated PLAN JSON with a command allowlist |
| `plan.py` | The executable plan schema Fable/agents must emit |

Everything under `aion_core/` is Python standard library only — no
third-party runtime dependency, by design (`docs/SERVER_DEPLOYMENT.md`
explains why this matters for a bare-metal install).

**LucyOS (this repo) is the operating system, not a project.** Every
separate repository/business it operates on is a *project*, tracked in
`PROJECTS/REGISTRY.md` with one folder each — `sevaa-sales-os/` is the only
one that exists so far. Adding a new business means adding a row and a
folder there, never restructuring the OS.

## 3. What is real vs. what is still a gap

### Built, tested, running — not aspirational
- 204 automated tests, passing; secret scanner clean
- Phone interface: built, pushed, load-tested with real HTTP round trips
- WhatsApp bridge: deterministic commands work with zero model calls
- SEVAA integration: 6 of 7 task packets merged; 3 remaining are written,
  tested and pushed pending only a mechanical PR merge (see §6)
- Mark-2 (DigitalOcean): hardened, running AION under systemd continuously
- Codex worker loop: claims one ranked task every 15 minutes, verifies its
  own result against real task status before pushing
- Fable readiness: **measured READY** as of this briefing (`aion fable-ready`)

### Genuine open gaps — in order of what blocks money
1. **No validated revenue experiment exists.** This is the actual
   bottleneck, not infrastructure. Queued as `TASK-1BB538FF`.
2. **The bridge has never had an adversarial security pass done for real**
   (one Class-A security review happened for S02's approval flow
   specifically; the bridge as a whole has not). Queued as `TASK-94945B7C`.
3. **T100 — the founder gate** (§6): five real-world actions only the owner
   can do. Nothing past this point is a coding problem.
4. **SEVAA main may have drifted** since the bundles were built on commit
   `a85a8cc` — must be re-verified before merging, not assumed.
5. **No second business exists yet.** SEVAA is the only revenue module. The
   directive's "portfolio of experiments" principle (kill weak ideas cheaply,
   fund what shows evidence) has not been applied to a second idea because
   the first has not yet produced a signal either way.

### Explicitly not a gap (already correctly refused/deferred)
- No paid model spend has happened (`used: INR 0` — correct, nothing has
  earned it yet)
- No outbound message has ever been sent to a real person (by design)
- `MODEL_API_KEY_CHEAP` is deliberately unset

## 4. How this makes money — the real path, not a projection

The mission is not "build a better AI tool." It is: **the owner and LucyOS
work through a portfolio of real ideas together**, using this infrastructure
to find, test and scale legal sources of income, killing weak ideas cheaply
and doubling down only where evidence justifies it. SEVAA Sales OS is the
first idea in that portfolio, not the only one it will ever run — a
FastAPI+SQLite B2B sales system for a real business (SevaaConnect Solutions,
architecture / interior design / modular construction). A second idea gets
its own row in `PROJECTS/REGISTRY.md` and its own folder, the same way.

The path, as designed, is not skippable:
```
idea -> market evidence -> cheap test -> real customer signal
     -> paid pilot -> delivery -> unit economics -> repeatability -> automation -> scale
```

**Where SEVAA actually is on that path right now:** built and tested, zero
real customers yet, zero real revenue yet. Milestone M0 (first real rupee)
is the very first rung, and it has not been reached. That is the honest
state, not a setback — it means the next real work is customer-facing, not
more code.

**T100 — the gate that unlocks it** (from `AION_TASK_QUEUE.md`), five owner
actions, none of them an agent's to do:
1. Authorise a hosting account (Railway, no-card trial) for the public app
2. Set four environment variables in that hosting account's own secret store
3. Choose which real mailbox is the public privacy contact
4. Name the first lawful traffic source — a real business decision
5. On the machine: set three secrets (`SEVAA_AUTOMATION_TOKEN`,
   `SEVAA_FOUNDER_TOKEN`, `SEVAA_NOTIFY_WEBHOOK_SECRET`)

Nothing past this point (T200/T300 — more automation, more integrations,
paid acquisition) unlocks until this gate is cleared with real evidence.

**What Fable's ₹700 should actually produce**, per its own generated brief:
one real experiment definition (offer, channel, buyer, price, cost ceiling,
success/failure numbers, the decision each outcome forces) and a security
review of the bridge — not more architecture. The system has enough
architecture; it does not yet have a tested revenue hypothesis.

## 5. The interface — what it is and how you use it

Two surfaces, same backend, same rules:

**WhatsApp** — plain-text commands, no model needed to answer them:
`status`, `money`, `tasks`, `blockers`, `approve <ID>`, `deny <ID>`, `pause`,
`resume`, `report`, `why <ID>`. This works even if every AI provider is down.

**Phone page** (`/app` on the bridge, port 8765) — the richer view:
1. **Money first** — real revenue/cost/net and a 7-day trend, forecasts kept
   visually separate so they can never be mistaken for real numbers
2. **What changed** — a feed of real completions, money events, failures
3. **Needs you** — approval cards (tap Approve/Deny, then confirm) and
   anything blocked on you
4. **Top tasks** — ranked by the same expected-value formula WhatsApp uses

A **+** button captures an idea/company/note in a few seconds, queues
offline if needed. Auth is a bearer token in `localStorage`, never a
password; the API refuses any request that looks credential-shaped, checked
by a real test, not an assumption. It is bound to `127.0.0.1` — you reach it
through an SSH tunnel, never an open port (`docs/SERVER_DEPLOYMENT.md`).

Both surfaces call the exact same `router.handle()` — an approval typed on
WhatsApp and one tapped on the phone are indistinguishable to the system.

## 6. What actually happens next, mechanically

1. Mark-2 finishes AION install + lands the 3 remaining SEVAA branches
   (Codex is working this from `deploy/CODEX_GO_LIVE.txt`)
2. The Codex worker loop keeps executing the ranked queue unattended
3. Owner runs one ₹700 Fable session on the 2-item queue in §3
4. Owner clears the T100 gate (§4) — the only non-delegable step
5. First real customer signal becomes possible; M0 becomes reachable

Everything before step 4 is infrastructure. Step 4 onward is the actual
business.
