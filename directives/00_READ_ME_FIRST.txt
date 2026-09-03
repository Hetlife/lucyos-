OPENCLAW / FABLE STARTUP PROMPT BUNDLE

Purpose
-------
This bundle gives OpenClaw, Fable, Claude, ChatGPT, Ollama/local workers, and future agents
a consistent operating hierarchy.

Recommended order
-----------------
1. Give 01_START_FABLE_BOOTSTRAP.txt to the primary Fable/Claude coding session.
2. Store 02_MASTER_AUTONOMOUS_OS_DIRECTIVE.txt as the highest project-level persistent prompt.
3. Store 03_AGENT_UNLAZY_EXECUTION_STANDARD.txt as the mandatory default for every worker/sub-agent.
4. Use 04_LOW_COST_WORKER_PROMPT.txt for Ollama / cheaper execution agents.
5. Use 05_SYNC_AND_HANDOFF_PROMPT.txt whenever work is transferred between ChatGPT, Claude, Fable, or OpenClaw.
6. Use 06_RESUME_AND_RECOVERY_PROMPT.txt when any session restarts, loses context, or changes models.
7. Use 07_OWNER_APPROVAL_AND_WHATSAPP_PROMPT.txt for owner approval gating and mobile-first control.

Core hierarchy
--------------
SYSTEM / PLATFORM / LAW
> CURRENT OWNER INSTRUCTION
> MASTER AUTONOMOUS OS DIRECTIVE
> AGENT UNLAZY EXECUTION STANDARD
> PROJECT-SPECIFIC INSTRUCTIONS
> CURRENT WORK ORDER
> HISTORICAL NOTES

Important
---------
- OpenClaw local shared state is the canonical operational source of truth.
- External chats are reasoning nodes, not authoritative memory.
- Do not claim an external chat is synced unless an actual sync path confirms it.
- Do not store literal credentials, tokens, API keys, passwords, private keys, or session cookies in these files.
- Real money, binding commitments, account ownership changes, credential exposure, and materially irreversible actions require explicit owner approval unless already covered by a specific existing authorization.
- A blocked approval must stop only that action, not all unrelated work.
