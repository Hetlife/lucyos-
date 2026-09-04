"""Generate OWNER_SETUP_REQUIRED.md — one batched ask, never drip-fed."""
from __future__ import annotations

from . import bootstrap, config, health, util

# Each requirement states the minimum permission and what resumes afterwards.
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
         resumes="WhatsApp becomes the live command surface; `aion serve` starts answering."),
    dict(tier="REQUIRED SOON", service="Phone interface token",
         secret="PHONE_API_TOKEN",
         purpose="Auth for the mobile page (bridges/web/phone.html) at /app — money-first "
                "status, approve from a tap, capture an idea offline",
         permission="Read/write to this machine's own AION state only, nothing external",
         action="On the Ubuntu PC run `aion secrets set PHONE_API_TOKEN` with a long random "
                "value, then open the page over your tunnel and paste the same value in "
                "once. Never send this token over WhatsApp.",
         security="Bearer token compared with hmac.compare_digest; bound to 127.0.0.1 by "
                  "default, so it only matters once you tunnel it out (Tailscale/ssh -L).",
         revoke="`aion secrets set PHONE_API_TOKEN` again with a new value, then re-enter it "
                "on the phone; the old value stops working immediately.",
         resumes="The phone page authenticates and shows live data."),
    dict(tier="REQUIRED NOW", service="GitHub (repo scope)",
         secret="GITHUB_TOKEN",
         purpose="Version control and safe collaboration for code and prompts",
         permission="Contents read/write on this repository only — no org admin, no delete",
         action="Create a fine-grained PAT, then on the PC run `aion secrets set GITHUB_TOKEN`.",
         security="Repo-scoped write. Never used as a secret store; a pre-commit scan blocks "
                  "credential-shaped content.",
         revoke="Delete the PAT in GitHub settings.",
         resumes="Automated commits, backups of prompts and state versioning."),
    dict(tier="REQUIRED SOON", service="Model provider API key (cheap class B)",
         secret="MODEL_API_KEY_CHEAP",
         purpose="Routine coding, research and structured work below the strong-model tier",
         permission="API access with a hard monthly spend cap set in the provider console",
         action="Set a provider-side monthly cap first, then run `aion secrets set MODEL_API_KEY_CHEAP`.",
         security="Spend is bounded twice: provider cap and the local budget governor.",
         revoke="Delete the key in the provider console.",
         resumes="Class B routing stops falling back and the queue drains faster."),
    dict(tier="REQUIRED SOON", service="Ollama (local models)",
         secret=None,
         purpose="Free local execution for classification, extraction and summarising",
         permission="Local install only, no account",
         action="On the PC: `curl -fsSL https://ollama.com/install.sh | sh` then "
                "`ollama pull llama3.1:8b`.",
         security="Runs entirely on your machine; no data leaves the PC.",
         revoke="`ollama rm <model>` or uninstall.",
         resumes="Class A routing becomes real, cutting cloud spend on routine work."),
    dict(tier="OPTIONAL LATER", service="Razorpay test credentials",
         secret="RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET",
         purpose="Payment plumbing for real revenue experiments",
         permission="Test mode only until a real product exists",
         action="Generate test keys in the Razorpay dashboard, then on the PC run "
                "`aion secrets set RAZORPAY_KEY_ID` and `aion secrets set RAZORPAY_KEY_SECRET`.",
         security="Test keys move no real money. Live keys require a separate approval.",
         revoke="Regenerate keys in the dashboard.",
         resumes="Checkout experiments can run end to end in sandbox."),
    dict(tier="OPTIONAL LATER", service="Hosting (Railway/Fly/VPS)",
         secret=None,
         purpose="Persistent production availability beyond the home PC",
         permission="Deploy only",
         action="Nothing yet. This is a paid decision and will arrive as a WhatsApp approval "
                "card with cost and downside before anything is bought.",
         security="No card details ever pass through chat.",
         revoke="Cancel the plan in the provider console.",
         resumes="Deployment of the already-prepared configuration."),
]


def render() -> str:
    h = health.run_all()
    lines = [
        "# OWNER SETUP REQUIRED",
        "",
        f"_Generated {util.now()}. One batched list — nothing here is asked twice._",
        "",
        "**Rule: never send a secret through WhatsApp.** Every credential below is entered "
        "directly on the Ubuntu PC into the local secret store. WhatsApp carries approvals only.",
        "",
    ]
    for tier in ("REQUIRED NOW", "REQUIRED SOON", "OPTIONAL LATER"):
        items = [r for r in REQUIREMENTS if r["tier"] == tier]
        lines += [f"## {tier}", ""]
        for r in items:
            have = bootstrap.has_secret(r["secret"].split(" / ")[0]) if r["secret"] else None
            state = "already set" if have else ("not set" if r["secret"] else "n/a")
            lines += [
                f"### {r['service']}  ·  {state}",
                f"- **Purpose**: {r['purpose']}",
                f"- **Minimum permission**: {r['permission']}",
                f"- **Exact owner action**: {r['action']}",
                f"- **Security impact**: {r['security']}",
                f"- **Revocation**: {r['revoke']}",
                f"- **What resumes afterwards**: {r['resumes']}",
                "",
            ]
    lines += ["## Current machine facts (measured, not assumed)", ""]
    for c in h["checks"]:
        lines.append(f"- `{c['name']}`: {'OK' if c['ok'] else 'ATTENTION'} — {c['detail']}")
    lines.append("")
    return "\n".join(lines)


def write() -> str:
    path = config.home() / "OWNER_SETUP_REQUIRED.md"
    util.atomic_write(path, render())
    return str(path)
