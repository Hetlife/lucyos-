"""Initial objective, decisions and task queue for a fresh install.

Written once, at first `aion seed`.  These are the genuine opening moves given
the measured state of a new system: no revenue, no credentials, no local model,
nothing deployed.  Re-running is safe — every item is keyed and skipped if it
already exists.
"""
from __future__ import annotations

from . import agents, db, memory, resume, tasks, util

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
