# STARTING PROMPT TEMPLATE

You are executing LucyOS Prompt Work Order `<PROMPT-ID>`.

1. Read `prompts/README.md`.
2. Locate only the exact prompt in `prompts/00_PENDING`.
3. Claim it using the LucyOS prompt-work-order mechanism; this must create/link a `SES-*` session and move the file to `01_PROCESSING` before execution.
4. Read the prompt fully, but treat repository/runtime evidence as higher authority than stale instructions.
5. Inspect live state before acting: branch/SHA, dirty state, active tasks/approvals, relevant service health, and whether another agent already completed the effect.
6. Execute the smallest safe solution under normal LucyOS authority/security/approval rules.
7. Use existing LucyOS skills before inventing new infrastructure.
8. Test and record evidence appropriate to the task.
9. If blocked or partial, leave the prompt in `01_PROCESSING`, update the session with the exact resume point, and stop safely.
10. If the work order is fully consumed, write an execution receipt and archive it. Archived means USED; the receipt must say SUCCESS, NOOP, or REJECTED explicitly.

Do not load archived prompts unless this work order references one by PROMPT-ID, SES-ID, project, or exact dependency.
Do not expose or store secrets in prompt files.
