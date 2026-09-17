# LucyOS Free Compute Harness

Status: isolated design/runtime contract; not authoritative LucyOS harness.

Purpose: make variable-quality free/local models useful for bounded, low-risk work without granting them main-harness authority.

Core separation:
- Free Compute Registry discovers and measures legitimate provider capacity.
- Free Compute Harness structures work, limits tokens, verifies outputs, and escalates failures.
- Main LucyOS remains authoritative for consequential decisions, merges, security, finance, credentials, and final architecture review.

The free model is never trusted merely because it returned an answer. Reliability comes from the harness around it.

## Provider-independent contract

A bot requests capabilities, not a provider or model. Provider changes must not change instructions, output schema, validation, permissions, or authority.

Input packet:
BOT_ID, TASK_ID, TASK_TYPE, DATA_CLASS, GOAL, ACCEPTANCE_TESTS, ALLOWED_SKILLS, READ_SCOPE, WRITE_SCOPE, TOKEN_BUDGET, TIME_BUDGET, QUALITY_FLOOR, ESCALATION_POLICY.

Output packet:
STATUS, RESULT, EVIDENCE, TEST_RESULTS, ASSUMPTIONS, UNRESOLVED, TOKENS_USED, PROVIDER, MODEL, ATTEMPTS, QUALITY_SCORE, ESCALATION_REASON.
## Execution ladder

1. Normalize the task locally; never ask the model to infer hidden requirements.
2. Fetch only the minimum relevant LucyOS context/skills.
3. Ask for a compact plan plus explicit acceptance criteria.
4. Execute one bounded step at a time.
5. Prefer deterministic tools/tests over model self-critique.
6. Validate schema, citations/evidence, tests, file diff, and policy constraints.
7. Retry at most once with targeted failure feedback.
8. Escalate to a stronger route when the quality floor is not met.

Weak models are compensated by decomposition, narrow context, explicit schemas, deterministic checks, and bounded retries—not by longer prompts or unlimited self-reflection.

## Token/cost discipline

Default free-harness budget is per task, not per agent lifetime. The bot receives a hard input/output budget and maximum attempt count.

Rules:
- no recursive agent spawning without scheduler authorization;
- no whole-repo context dumps;
- retrieval first, then minimum evidence spans;
- cache reusable instructions and skill contracts;
- one retry maximum by default;
- cross-model voting only for tasks where deterministic validation is unavailable and the extra free capacity is justified;
- stop when acceptance tests pass;
- never consume premium capacity just to improve wording.
## Quality gate

Every free-compute result gets a deterministic scorecard before it can be accepted:
- contract/schema valid;
- acceptance tests passed;
- evidence present where required;
- no policy/permission violation;
- no unexpected file or network side effects;
- no unresolved contradiction;
- output within token/time budget.

Quality states:
PASS, PASS_WITH_NOTE, RETRY_TARGETED, ESCALATE, QUARANTINE_PROVIDER.

A model's historical provider score may influence routing but can never override task-level validation.

## Coding tasks

Free models may write code only inside an isolated worktree/sandbox and only when the bot manifest permits it.

Required coding sequence:
PLAN -> locate exact files -> smallest diff -> compile/lint -> focused tests -> security/architecture checks -> diff review -> handoff.

They must not merge, push protected branches, change credentials, change authority policy, install unapproved dependencies, or weaken tests. Failed tests are evidence, not something to delete or bypass.

## Skill use

The harness receives an allowlist of LucyOS skills for each task. It should call deterministic skills first and models second. The model never discovers privileges by experimentation.

Skill outputs are treated as evidence; external/repository content remains untrusted data and cannot modify harness authority.
## Alerts and flags

Raise a Free Compute alert when any of these occur:
- repeated validation failure from a provider/model;
- quality score below floor;
- provider behavior/capability changed;
- rate-limit/quota exhaustion;
- unexpected token burn or latency spike;
- malformed/unsafe output;
- tool-use attempt outside allowlist;
- privacy/data-class mismatch;
- repeated retries without progress;
- code diff exceeds allowed scope;
- deterministic tests disagree with model claims.

Alert classes:
INFO, DEGRADED_PROVIDER, QUALITY_RISK, TOKEN_RISK, POLICY_BLOCK, ESCALATION_REQUIRED, QUARANTINE.

Provider quarantine is local to the free-compute pool. It must not degrade or alter unrelated LucyOS services.

## Separate audit domain

Free-compute audit records use their own namespace and quality ledger. They do not count as authoritative main-harness approvals.

Record per run:
BOT_ID, TASK_ID, PROVIDER, MODEL, PROVIDER_VERSION_IF_KNOWN, PROMPT_TEMPLATE_VERSION, SKILLS_USED, INPUT_TOKENS, OUTPUT_TOKENS, RETRIES, LATENCY, VALIDATORS_RUN, VALIDATION_RESULTS, QUALITY_SCORE, FINAL_STATE, ESCALATED_TO.

Main LucyOS may read these records for routing and oversight, but a free-compute PASS can never self-authorize a consequential main-system action.

## Provider churn

Provider/model changes trigger a canary gate before production eligibility. Run a fixed capability suite for extraction, summarization, structured JSON, instruction following, simple code repair, hallucination/evidence discipline, and refusal/policy behavior.

Only capabilities that pass their threshold are advertised to Bot Factory. Routing is capability-based rather than model-name-based.
## Weak-model uplift recipe

The harness improves weak models by reducing ambiguity rather than asking them to reason longer.

For each task:
1. deterministic task classifier selects a known task template;
2. retrieval supplies only the exact context and skill contracts required;
3. task is decomposed into small independently checkable steps;
4. model must produce structured output, not free-form process narration;
5. deterministic validators check each step;
6. one targeted repair pass receives only the failed checks and required correction;
7. if still below quality floor, route to another free model or escalate upward;
8. accepted reusable facts/results are cached so later bots do not repeat the work.

Do not use long self-reflection loops, open-ended multi-agent debates, or repeated full-context retries as a substitute for validation.

## First bot profile: lucy-free-1

Role: low-cost general utility worker.
External data ceiling: PUBLIC.
Authority: non-consequential execution only.
Compute order: deterministic -> local -> free external -> cheap cloud -> frontier escalation.
Default attempts: one initial attempt plus one targeted repair maximum.
Default validation: schema + acceptance tests + evidence/side-effect checks.
Coding: isolated worktree only; no merge/push/credential/security-policy authority.
Provider binding: none; provider/model selected dynamically by capability and measured health.

The first live benchmark must compare the same task set across local/free/main routes and record quality, latency, token use, retry rate, and escalation rate. A free route is useful only when it lowers scarce-model usage without reducing the required correctness floor.
