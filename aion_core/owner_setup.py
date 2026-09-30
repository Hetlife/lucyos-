"""Generate OWNER_SETUP_REQUIRED.md — one batched ask, based on measured
capability, never drip-fed, and never asking for something already working."""
from __future__ import annotations

from . import bootstrap, config, health, util, worker

# What the shipped aion-bridge.service (the Meta Cloud API adapter) refuses to
# start without. aion_core must not import from bridges/, so this is a separate
# list; tests/test_owner_setup.py compares it with
# bridges/whatsapp_bridge.py:CLOUD_ENV_REQUIRED so the two cannot drift apart.
# All six go through `aion secrets set` because the service only loads
# private_state/secrets.env.
CLOUD_BRIDGE_VARS = ("WHATSAPP_ACCESS_TOKEN", "WHATSAPP_PHONE_NUMBER_ID",
                     "WHATSAPP_VERIFY_TOKEN", "WHATSAPP_APP_SECRET",
                     "WHATSAPP_GRAPH_API_VERSION", "WHATSAPP_ALLOWED_SENDER")

# Each requirement states the minimum permission and what resumes afterwards.
# `satisfied(caps)` decides — from measured state, never a guess — whether the
# owner action is still needed at all; `satisfied_detail(caps)` explains why
# not when it isn't.
REQUIREMENTS = [
    dict(tier="REQUIRED NOW", service="WhatsApp bridge (OpenClaw)",
         secret="WHATSAPP_BRIDGE_TOKEN",
         purpose="Owner remote control and approval channel from iPhone",
         permission="Send/receive messages for your own number only",
         action="On the Ubuntu PC run `aion secrets set WHATSAPP_BRIDGE_TOKEN` and paste the "
                "bridge token at the prompt. Do not send it over WhatsApp.",
         security="Token allows sending messages as the bridge account; it is stored 0600 "
                  "in private_state/secrets.env and never enters git, logs or chat.",
         revoke="Rotate/revoke in the bridge provider console, then re-run the same command.",
         resumes="WhatsApp becomes the live command surface once the bridge service is installed and running (`scripts/install_services.sh` prints the exact start command for this platform).",
         satisfied=lambda c: c["openclaw_present"] or c["legacy_bridge_credential_present"],
         satisfied_detail=lambda c: (
             "WHATSAPP_BRIDGE_TOKEN already set" if c["legacy_bridge_credential_present"] else
             f"OpenClaw installation detected on this machine ({c['openclaw_evidence']}); "
             "owner-channel end-to-end reachability NOT YET PROVEN — presence is not "
             f"proof WhatsApp is live. AION loopback/openclaw_port reconciliation "
             f"({c['openclaw_gateway_detail']}) belongs to R-05, not this owner ask")),
    dict(tier="REQUIRED NOW", service="WhatsApp Cloud API bridge (aion-bridge.service)",
         secret=", ".join(CLOUD_BRIDGE_VARS),
         purpose="Direct Meta WhatsApp Cloud API channel. The shipped bridge service exits "
                 "at start unless all six values below are set. Needed only if you run this "
                 "bridge; skip it if OpenClaw carries WhatsApp for you.",
         permission="Cloud API access for your own WhatsApp Business number only; replies go "
                    "only to WHATSAPP_ALLOWED_SENDER",
         action="Take the values from your Meta app console, then on the PC run "
                "`aion secrets set <NAME>` once for each: "
                "WHATSAPP_ACCESS_TOKEN (app access token); "
                "WHATSAPP_APP_SECRET (app secret, used to verify inbound signatures); "
                "WHATSAPP_VERIFY_TOKEN (a value you invent, then paste the same value into "
                "the Meta webhook setup; use only letters, digits, - and _ because the "
                "service loads the secret store through a shell and any other character "
                "can silently corrupt it); "
                "WHATSAPP_PHONE_NUMBER_ID (numeric id of the sending number); "
                "WHATSAPP_ALLOWED_SENDER (your own number exactly as Meta reports it in the "
                "message `from` field: digits only, no + or spaces; it is an exact-match "
                "allowlist); "
                "WHATSAPP_GRAPH_API_VERSION (the Graph API version your Meta app uses, copied "
                "from the console; it is explicit on purpose so provider upgrades never "
                "happen silently). Even the non-secret ones go through `aion secrets set`: "
                "the service loads only private_state/secrets.env. Do not send any of them "
                "over WhatsApp.",
         security="The access token can send messages as your business number and the app "
                  "secret authenticates inbound traffic; both are stored 0600 in "
                  "private_state/secrets.env and never enter git, logs or chat.",
         revoke="Rotate the token and app secret in the Meta app console, then re-run "
                "`aion secrets set` for each.",
         resumes="The bridge service can start (`scripts/install_services.sh` prints the "
                 "start command for this platform); Meta still needs a public HTTPS "
                 "callback URL (see R-03).",
         satisfied=lambda c: not c["cloud_bridge_missing"],
         satisfied_detail=lambda c: "all six WhatsApp Cloud API values are set"),
    dict(tier="REQUIRED NOW", service="GitHub (repo scope)",
         secret="GITHUB_TOKEN",
         purpose="Version control and safe collaboration for code and prompts",
         permission="Contents read/write on this repository only — no org admin, no delete",
         action="Create a fine-grained PAT, then on the PC run `aion secrets set GITHUB_TOKEN`.",
         security="Repo-scoped write. Never used as a secret store; a pre-commit scan blocks "
                  "credential-shaped content.",
         revoke="Delete the PAT in GitHub settings.",
         resumes="Automated commits, backups of prompts and state versioning.",
         defer_until_probe=True,
         verify_action="Run `aion owner-setup` on a connected host. It will verify the existing "
                       "remote with a read check and a non-mutating dry-run push before asking "
                       "for any new credential.",
         satisfied=lambda c: c["github_write_ok"] or c["github_credential_present"],
         satisfied_detail=lambda c: (
             "GITHUB_TOKEN already set" if c["github_credential_present"] else
             f"Existing git remote already has proven write access — {c['github_write_detail']}")),
    dict(tier="REQUIRED SOON", service="Model provider API key (cheap class B)",
         secret="MODEL_API_KEY_CHEAP",
         purpose="Routine coding, research and structured work below the strong-model tier",
         permission="API access with a hard monthly spend cap set in the provider console",
         action="Set a provider-side monthly cap first, then run `aion secrets set MODEL_API_KEY_CHEAP`.",
         security="Spend is bounded twice: provider cap and the local budget governor.",
         revoke="Delete the key in the provider console.",
         resumes="Class B routing stops falling back and the queue drains faster.",
         satisfied=lambda c: c["cloud_worker"] or c["model_credential_present"],
         satisfied_detail=lambda c: (
             "MODEL_API_KEY_CHEAP already set" if c["model_credential_present"] else
             f"A configured cloud worker already provides class B routing ({c['cloud_worker_cmd']})")),
    dict(tier="REQUIRED SOON", service="Ollama (local models)",
         secret=None,
         purpose="Free local execution for classification, extraction and summarising",
         permission="Local install only, no account",
         action="On the PC: `curl -fsSL https://ollama.com/install.sh | sh` then "
                "`ollama pull llama3.1:8b`.",
         security="Runs entirely on your machine; no data leaves the PC.",
         revoke="`ollama rm <model>` or uninstall.",
         resumes="Class A routing becomes real, cutting cloud spend on routine work.",
         satisfied=lambda c: c["ollama"],
         satisfied_detail=lambda c: "Ollama already installed with local models available"),
    dict(tier="OPTIONAL LATER", service="Razorpay test credentials",
         secret="RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET",
         purpose="Payment plumbing for real revenue experiments",
         permission="Test mode only until a real product exists",
         action="Generate test keys in the Razorpay dashboard, then on the PC run "
                "`aion secrets set RAZORPAY_KEY_ID` and `aion secrets set RAZORPAY_KEY_SECRET`.",
         security="Test keys move no real money. Live keys require a separate approval.",
         revoke="Regenerate keys in the dashboard.",
         resumes="Checkout experiments can run end to end in sandbox.",
         satisfied=lambda c: c["razorpay_keys"],
         satisfied_detail=lambda c: "Razorpay test keys already set"),
    dict(tier="OPTIONAL LATER", service="Hosting (Railway/Fly/VPS)",
         secret=None,
         purpose="Persistent production availability beyond the home PC",
         permission="Deploy only",
         action="Nothing yet. This is a paid decision and will arrive as a WhatsApp approval "
                "card with cost and downside before anything is bought.",
         security="No card details ever pass through chat.",
         revoke="Cancel the plan in the provider console.",
         resumes="Deployment of the already-prepared configuration.",
         satisfied=lambda c: False,
         satisfied_detail=lambda c: ""),
]


def _capabilities(*, probe_external: bool = False) -> dict:
    """Measured capability snapshot with external probes opt-in.

    Bootstrap stays local-first and deterministic. Network-backed Git probes run
    only for the explicit `aion owner-setup` command, never as a side effect of
    `aion init` or ordinary health/status work.
    """
    caps = worker.capability_report()
    if probe_external:
        gh = health.check_github_remote()
        gh_write = health.check_github_write()
    else:
        gh = {"ok": False, "detail": "not probed during local bootstrap"}
        gh_write = {"ok": False, "detail": "not probed during local bootstrap"}
    oc = health.openclaw()
    oc_gateway = health.check_openclaw()
    if oc["executable_on_path"]:
        evidence = f"executable at {oc['executable_on_path']}"
    else:
        evidence = f"home contents: {', '.join(oc['home_contents'][:4]) or 'none'}"
    return {
        "ollama": caps["ollama"],
        "cloud_worker": caps["cloud_worker"],
        "cloud_worker_cmd": caps["cloud_worker_cmd"],
        "model_credential_present": bootstrap.has_secret("MODEL_API_KEY_CHEAP"),
        "github_remote_ok": gh["ok"],
        "github_remote_detail": gh["detail"],
        "github_write_ok": gh_write["ok"],
        "github_write_detail": gh_write["detail"],
        "github_probe_performed": probe_external,
        "github_credential_present": bootstrap.has_secret("GITHUB_TOKEN"),
        "openclaw_present": oc["present"],
        "openclaw_evidence": evidence,
        "openclaw_gateway_detail": oc_gateway["detail"],
        "legacy_bridge_credential_present": bootstrap.has_secret("WHATSAPP_BRIDGE_TOKEN"),
        "cloud_bridge_missing": [n for n in CLOUD_BRIDGE_VARS if not bootstrap.has_secret(n)],
        "razorpay_keys": (bootstrap.has_secret("RAZORPAY_KEY_ID")
                           and bootstrap.has_secret("RAZORPAY_KEY_SECRET")),
    }


def render(*, probe_external: bool = False) -> str:
    h = health.run_all()
    caps = _capabilities(probe_external=probe_external)
    lines = [
        "# OWNER SETUP REQUIRED",
        "",
        f"_Generated {util.now()}. One batched list, built from measured machine state — "
        "nothing already working is asked for again._",
        "",
        "**Rule: never send a secret through WhatsApp.** Every credential below is entered "
        "directly on the Ubuntu PC into the local secret store. WhatsApp carries approvals only.",
        "",
    ]
    satisfied_items = []
    verification_items = []
    for tier in ("REQUIRED NOW", "REQUIRED SOON", "OPTIONAL LATER"):
        pending = []
        for r in [x for x in REQUIREMENTS if x["tier"] == tier]:
            if r["satisfied"](caps):
                satisfied_items.append(r)
            elif r.get("defer_until_probe") and not caps.get("github_probe_performed", False):
                verification_items.append(r)
            else:
                pending.append(r)
        if not pending:
            continue
        lines += [f"## {tier}", ""]
        for r in pending:
            lines += [
                f"### {r['service']}  ·  not set",
                f"- **Purpose**: {r['purpose']}",
                f"- **Minimum permission**: {r['permission']}",
                f"- **Exact owner action**: {r['action']}",
                f"- **Security impact**: {r['security']}",
                f"- **Revocation**: {r['revoke']}",
                f"- **What resumes afterwards**: {r['resumes']}",
                "",
            ]
    if verification_items:
        lines += ["## VERIFY EXISTING CAPABILITY — no new credential yet", ""]
        for r in verification_items:
            lines += [
                f"- **{r['service']}**: existing access was not network-probed during local bootstrap.",
                f"  **Next safe check**: {r['verify_action']}",
            ]
        lines.append("")
    if satisfied_items:
        lines += ["## Already satisfied — no owner action needed", ""]
        for r in satisfied_items:
            lines.append(f"- **{r['service']}**: {r['satisfied_detail'](caps)}")
        lines.append("")
    lines += ["## Current machine facts (measured, not assumed)", ""]
    for c in h["checks"]:
        lines.append(f"- `{c['name']}`: {'OK' if c['ok'] else 'ATTENTION'} — {c['detail']}")
    lines.append(f"- `github_remote`: {'OK' if caps['github_remote_ok'] else 'ATTENTION'} — "
                  f"{caps['github_remote_detail']}")
    lines.append(f"- `github_write`: {'OK' if caps['github_write_ok'] else 'ATTENTION'} — "
                  f"{caps['github_write_detail']}")
    lines.append("")
    return "\n".join(lines)


def write(*, probe_external: bool = False) -> str:
    path = config.home() / "OWNER_SETUP_REQUIRED.md"
    util.atomic_write(path, render(probe_external=probe_external))
    return str(path)
