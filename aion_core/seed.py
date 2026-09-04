"""Initial objective, decisions and task queue for a fresh install.

Written once, at first `aion seed`.  These are the genuine opening moves given
the measured state of a new system: no revenue, no credentials, no local model,
nothing deployed.  Re-running is safe — every item is keyed and skipped if it
already exists.
"""
from __future__ import annotations

from . import agents, db, memory, resume, tasks, util

MISSION = (
    "Run a portfolio of businesses autonomously and produce INR 1,00,000 per month "
    "of real, evidenced net profit, with the owner's involvement limited to approvals "
    "sent from a phone. Real capital is injected later, once the machinery is proven.")

# Milestones toward the mission.  Each is a measurement, never a projection, and
# each must be proved before the next is attempted.
MILESTONES = [
    ("M0", "First real rupee", "one ACTUAL revenue row carrying a transaction reference"),
    ("M1", "First repeat customer", "the same payer pays twice without the owner prompting"),
    ("M2", "Unit economics proven",
     "revenue minus every attributable cost is positive across at least 10 deliveries"),
    ("M3", "One business hands-off for 30 days",
     "30 consecutive days in which the owner approved but never operated"),
    ("M4", "INR 25,000/month net", "three consecutive months at or above, all ACTUAL"),
    ("M5", "Second business onboarded",
     "a second project reaches M2 reusing this machinery rather than a rewrite"),
    ("M6", "INR 1,00,000/month net", "three consecutive months at or above, all ACTUAL"),
]

OBJECTIVE = ("Reach the first rupee of real, evidenced revenue while the owner's "
             "involvement stays limited to approvals sent from WhatsApp.")

DECISIONS = [
    ("state ownership",
     "The Ubuntu PC holds canonical state; WhatsApp is a control surface only",
     "A chat app cannot be a database. If WhatsApp, a model provider or the network "
     "goes down, the PC must still know everything and be able to resume."),
    ("command surface",
     "Owner commands are answered by deterministic code, not by a model",
     "Reading `status` does not need intelligence. Making the control channel free "
     "and always-available matters more than making it conversational."),
    ("authorization form",
     "Only the exact form APPROVE <ID> or DENY <ID> decides an approval",
     "Casual agreement in chat is ambiguous and easy to manufacture. A unique id "
     "per consequential action makes intent unmistakable and auditable."),
    ("secrets channel",
     "No credential ever travels through WhatsApp; values are entered on the PC",
     "Chat history is stored on third-party servers and on the phone. The secret "
     "store is 0600, excluded from backups and from git."),
    ("spend order",
     "Deterministic code first, then local model, then cheap cloud, then strong model",
     "Most of this workload is mechanical. Paying a strong model to format text or "
     "count rows is waste that compounds daily."),
    ("mission scope",
     "Nothing in the control layer may be hard-coded to one business",
     "A lakh a month from a single lucky offer is not the goal; machinery that onboards "
     "the next business without a rewrite is. Every project carries its own `project` key "
     "and anything business-specific lives in PROJECTS/, never in aion_core/."),
    ("growth honesty",
     "A milestone counts only when measured, never when projected",
     "The path runs M0 to M6 in order. Skipping one because a spreadsheet says the next is "
     "reachable is how a system convinces its owner it is working while earning nothing."),
    ("money honesty",
     "Revenue is only ACTUAL with transaction evidence; forecasts stay labelled",
     "A forecast recorded as revenue makes the whole system lie to its owner about "
     "the one number that decides whether any of this is worth continuing."),
]

# (title, kwargs) — the opening queue.  Class C items are the genuine
# high-value reasoning jobs; everything else is delegated downward.
TASKS = [
    ("Design the first real revenue experiment end to end", dict(
        model_class="C", priority=1, impact=5, probability=0.6, unlocks=3, info_gain=3,
        cost=1, risk=1, time_est=2,
        description="Pick one offer, one channel and one buyer type. Define unit economics, "
                    "the minimum valid test, the cost ceiling, the success and failure "
                    "conditions, and the decision the result triggers. Real money only.",
        success_criteria="A written experiment with hypothesis, baseline, success and failure "
                         "conditions, max cost, time window and the decision each outcome forces",
        validation_method="Recorded as a decision plus an experiment file, with the first "
                          "executable step queued as its own task",
        next_action="Read FABLE_CONTEXT.md, then write the experiment")),
    ("Decompose the revenue path into executable work orders", dict(
        model_class="C", priority=1, impact=5, probability=0.7, unlocks=4, info_gain=2,
        cost=1, risk=1, time_est=2, dependencies="@0",
        description="Turn the chosen experiment into a task graph a cheap or local model can "
                    "execute without re-reasoning: dependencies, order, success criteria, "
                    "tests, expected artifacts.",
        success_criteria="Every leaf task carries a success criterion and a validation method, "
                         "and is routed to the cheapest class that can do it",
        next_action="Run `aion context <TASK_ID>` for each leaf and save the work orders")),
    ("Design and build the AION phone interface (backend + UI)", dict(
        model_class="C", kind="architecture", priority=1, impact=5, probability=0.75,
        unlocks=3, info_gain=2, cost=1, risk=2, time_est=3,
        description=(
            "The owner runs this from an iPhone. WhatsApp covers commands and approvals; "
            "this is the richer surface for reading state and acting quickly.\n\n"
            "BACKEND — hosted on the Ubuntu PC / OpenClaw, never a third party:\n"
            "  - Extend bridges/whatsapp_bridge.py's HTTP server, or add bridges/http_server.py, "
            "serving a small JSON API over localhost plus the LAN address.\n"
            "  - Endpoints, all read-only except the last: GET /api/status, /api/tasks, "
            "/api/blockers, /api/money, /api/errors, /api/agents, /api/report; "
            "POST /api/command {message} routed through router.handle so the phone and "
            "WhatsApp share exactly one command implementation.\n"
            "  - Auth: a bearer token compared with hmac.compare_digest, read from the 0600 "
            "secret store. No cookies, no login form, no third-party auth.\n"
            "  - Bind 127.0.0.1 by default; reaching it from outside the house is the owner's "
            "tunnel (Tailscale or ssh -L), documented, never an open port.\n"
            "  - Every response already passes security.redact; keep it that way.\n\n"
            "UI — one mobile-first page, installable to the home screen:\n"
            "  - Thumb-reachable: status at the top, a single action list, big tap targets, "
            "no horizontal scrolling, readable at arm's length in sunlight.\n"
            "  - Approval cards render with APPROVE and DENY as two large buttons that post "
            "the exact command form; a confirm step prevents a fat-finger approval.\n"
            "  - Local storage: cache the last status, tasks and blockers so the page opens "
            "instantly and still shows the last known state with an explicit 'as of' time "
            "when the PC is unreachable. Never cache anything from /api/report that could "
            "carry sensitive operational detail beyond the session.\n"
            "  - The token lives in localStorage, is enterable once, and is clearable with a "
            "visible 'forget this device' control.\n"
            "  - Dark and light, system-following. No external fonts, scripts or CDNs, so it "
            "works with the house internet down.\n\n"
            "SCREENS the owner actually needs:\n"
            "  1. MONEY FIRST. The top of the page answers, in this order: am I making money, "
            "how much, from where. Per project: real revenue, real cost, net, and the trend "
            "since last week. Projections appear only under a separate labelled heading, "
            "never mixed into the real figures.\n"
            "  2. WHAT CHANGED. A short feed of what actually happened since the owner last "
            "looked: tasks completed with their evidence, money in, failures, decisions "
            "taken. Not a log dump.\n"
            "  3. NEEDS YOU. Every open approval as a card, plus anything blocked on the "
            "owner. This is the only place the system asks for anything.\n"
            "  4. TAP TO ADD. One prominent button to capture an idea, a company, a project "
            "or a note in a few seconds, offline-capable: it queues locally and posts when "
            "the PC is reachable. It writes through router.handle, so it lands in the same "
            "triage queue as a WhatsApp message. Let the owner tag it as idea / company / "
            "project so it creates the right thing.\n"
            "  5. FEEDBACK THAT MOVES WORK. Where the system presents an option, a draft or "
            "a proposed direction, the owner can react in one tap (yes / no / this one) and "
            "optionally type a line. That reaction must change what the machine does next: "
            "it writes a decision and updates the task, it is not a comment box. Multiple "
            "choices render as choice cards, one tap each.\n\n"
            "ALREADY BUILT AND TESTED (do not redo): aion_core/intake.py — capture() for "
            "idea/company/project/note with dedup and credential refusal, feedback() that "
            "writes a decision and moves the task, feed() for what-changed; "
            "metrics.by_project() and metrics.trend() for money-first. What remains is the "
            "HTTP layer and the page.\n\n"
            "Decompose the build into a PLAN so cheap models implement it; you design and "
            "review, you do not hand-write every line."),
        success_criteria=(
            "The owner opens the page on their iPhone over the tunnel, sees live status, "
            "approves a real approval from it, and the same page still renders the last "
            "known state with the PC switched off"),
        validation_method="New tests covering auth rejection, redaction of every endpoint, "
                          "and the approve round trip; plus a screenshot from the phone",
        next_action="Write the API surface and the plan, then `aion plan apply`")),
    ("Adversarially review the bridge's external exposure", dict(
        model_class="C", priority=2, impact=4, probability=0.8, unlocks=2, info_gain=2,
        cost=1, risk=1, time_est=1,
        description="The webhook is the only inbound path from the internet to the machine. "
                    "Attack it: replay, forged sender, oversized payload, injection through "
                    "message text, token handling, what a compromised bridge could reach.",
        success_criteria="Each finding is either fixed with a test or recorded with a reason "
                         "for accepting it",
        validation_method="New tests in tests/test_bridge.py covering each fixed finding",
        next_action="Read bridges/whatsapp_bridge.py and aion_core/router.py")),
    ("Install Ollama and route class A work to it", dict(
        model_class="DET", priority=2, impact=3, probability=0.9, unlocks=2, cost=1, risk=1,
        description="Local models make classification, extraction, summarising and log parsing "
                    "free. Until it exists, class A work falls through to paid cloud calls.",
        success_criteria="`aion health` reports installed models and a class A task completes "
                         "locally with evidence",
        next_action="curl -fsSL https://ollama.com/install.sh | sh && ollama pull llama3.1:8b")),
    ("Connect the WhatsApp bridge to the real transport", dict(
        model_class="B", priority=1, impact=5, probability=0.7, unlocks=3, cost=1, risk=2,
        human_dependence=2,
        description="The bridge answers correctly on stdin and file adapters. It needs a real "
                    "transport and its token before the phone can drive the system.",
        success_criteria="A message sent from the owner's phone returns a status reply",
        validation_method="End-to-end message from the real phone, recorded as evidence",
        next_action="aion secrets set WHATSAPP_BRIDGE_TOKEN, then start aion-bridge.service")),
    ("Record the true current financial position", dict(
        model_class="DET", priority=2, impact=3, probability=0.95, cost=1, risk=1,
        description="Every recurring cost and every rupee actually received, with evidence. "
                    "Without this the net number is fiction.",
        success_criteria="`aion money` shows real revenue, real cost and net, each backed by "
                         "a transaction reference",
        next_action="aion money-add cost <amount> --evidence <reference> for each live cost")),
    ("Define the milestone ladder to INR 1,00,000/month and instrument M0", dict(
        model_class="C", kind="finance_reason", priority=1, impact=5, probability=0.7,
        unlocks=3, info_gain=3, cost=1, risk=1, time_est=2,
        description=(
            "The mission is INR 1,00,000/month of real net profit across a portfolio of "
            "businesses, run autonomously, with real capital injected later.\n\n"
            "Work out what must be true at each milestone M0-M6: the offer, the unit "
            "economics, the delivery cost including model spend, the capital the owner would "
            "need to inject and when, and the point at which a second business can be "
            "onboarded without rewriting anything.\n\n"
            "State plainly which milestones this machinery can reach unassisted and which "
            "need a capability that does not exist yet, then queue those capabilities as "
            "tasks. Instrument M0 so reaching it is detected, not claimed."),
        success_criteria=("Each milestone has a number, a proof method and the capability it "
                          "needs; M0 is detected automatically by `aion money`"),
        validation_method="A recorded decision plus queued capability tasks",
        next_action="Read the mission and milestones in memory, then write the ladder")),
    ("Set up an encrypted off-machine backup of private_state", dict(
        model_class="DET", priority=3, impact=4, probability=0.9, cost=1, risk=1,
        description="Backups deliberately exclude secrets, so the secret store has no copy. "
                    "A disk failure would currently cost every credential.",
        success_criteria="An encrypted copy exists off the machine and has been restore-tested",
        next_action="Choose the medium, then write the script")),
]


def apply() -> dict:
    """Seed the objective, decisions and opening queue.  Idempotent."""
    result = {"decisions": 0, "tasks": [], "skipped": 0}
    if db.get_meta("seeded_at"):
        result["skipped"] = 1
        return result

    memory.remember("preference", "mission", MISSION,
                    confidence="VERIFIED_FACT", source="owner directive")
    for code, name, proof in MILESTONES:
        memory.remember("fact", f"milestone {code} {name}",
                        f"{name}. Proved by: {proof}. Status: not reached.",
                        confidence="VERIFIED_FACT", source="mission ladder")
    memory.remember("preference", "owner objective", OBJECTIVE,
                    confidence="VERIFIED_FACT", source="owner directive")
    for subject, decision, rationale in DECISIONS:
        memory.decide(subject, decision, rationale=rationale,
                      evidence="owner directive bundle in directives/",
                      confidence="VERIFIED_FACT", made_by="owner")
        result["decisions"] += 1

    created: list[str] = []
    for title, kw in TASKS:
        kw = dict(kw)
        # "@n" means "depends on the nth seeded task", resolved once ids exist.
        deps = kw.get("dependencies", "")
        if deps.startswith("@"):
            kw["dependencies"] = created[int(deps[1:])]
        created.append(tasks.create(title, **kw))
    result["tasks"] = created

    agents.seed_defaults()
    db.set_meta("seeded_at", util.now())
    resume.checkpoint(
        objective=OBJECTIVE,
        current_state="control layer built and tested; no credentials, no local model, "
                      "no revenue yet",
        bottleneck="no validated revenue experiment exists yet",
        files_to_read="FABLE/FABLE_CONTEXT.md, FABLE/FABLE_TASK_QUEUE.md, RESUME.md",
    )
    return result
