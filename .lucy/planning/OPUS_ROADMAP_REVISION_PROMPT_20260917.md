# Opus Revision Prompt — LucyOS / Mark-2 Integration Roadmap

You are performing a **second, compact planning pass** on LucyOS / Mark-2.

This pass is **planning only**. Do not merge, implement, refactor, execute the queue, modify governance, or spend time re-deriving already verified repository facts.

## Read first

1. `.lucy/planning/INTEGRATION_ROADMAP_20260917.md`
2. The current repository state at `integration/consolidation-20260916`
3. The implementation seams specifically named below only where needed to verify the corrections.

Treat Part 0 of the roadmap as ground truth unless the repository directly contradicts it. Keep token use low. Do not reproduce source files or repeat the full roadmap.

## Goal

Revise the roadmap into a **corrected V2 planning skeleton** that can be handed to another high-capability reviewer for final implementation detail, and then converted into bounded Codex instructions.

Preserve the existing architecture: one canonical shared brain, one execution loop, existing AION state/database, existing scheduler/timers, existing authority gates, existing singleton lock, existing evidence gates, existing restart/resume, existing LearnRepo lease pattern, and existing executor hierarchy.

Do not create a second loop, scheduler, state store, governance system, or self-modifying Codex mechanism.

## Corrections from external repo review

Incorporate these explicitly. Do not silently ignore or dilute them.

### 1. Normalize the Codex result contract

The repository currently has two incompatible result formats:

- `scripts/aion_codex_worker.sh` asks for:
  `STATUS / ACTIONS / FILES_CHANGED / TESTS / RESULTS / BLOCKERS / NEXT_ACTION`
- `aion_core/context.py` currently asks for a different 11-field packet.

V2 must define **one canonical packet**. Prefer the existing seven-field worker boundary unless repository evidence gives a stronger reason otherwise.

The V2 plan must include a bounded integration task to make every producer/consumer agree on that same contract.

### 2. Do not claim the result parser already exists

Current `worker.py` receives cloud-worker stdout and independently validates the task, but does not yet parse a typed `AGENTS/results/<TASK_ID>.md` packet as described by the original skeleton.

V2 must distinguish:
- what already exists,
- what needs to be added inside the existing worker seam,
- and what must remain independent validation rather than model self-report.

The worker must continue to run the task's own `validation_command` independently. Codex saying `STATUS: DONE` is never completion proof.

### 3. Codex governance protection must become structural

Current `aion_codex_worker.sh` uses Codex with workspace write access. Prompt wording alone does not make `AGENTS/prompts/**` or `.lucy/authority/**` unwritable.

V2 must require a mechanical protection design before unattended Codex is considered fully safe.

At minimum the plan must include:
- pre-run changed-state capture,
- post-run changed-path verification,
- rejection of any result touching governance paths,
- error/finding recording,
- recovery to clean task state,
- strict/anti-dup authority verification.

Also distinguish between:
- detection + rejection after an attempted write, and
- true path-level write impossibility.

If true path-level immutability depends on Codex sandbox or OS capabilities not yet verified, mark that as an explicit owner/implementation decision rather than pretending it already exists.

### 4. Work-order fields must bind to existing canonical task state

Do not invent a parallel state store or silently invent canonical columns.

Existing task fields include:
`task_id`, `project`, `title`, `description`, `status`, `priority`, `model_class`, `dependencies`, `blockers`, `success_criteria`, `validation_method`, `output_location`, `exec_command`, `validation_command`, `evidence`, `next_action`, `last_error`.

A base SHA may be used only as execution provenance/envelope metadata unless a canonical field is explicitly approved later.

Task-specific path/scope constraints must reuse existing task semantics and authority rules rather than introducing another canonical database.

### 5. Fix authority-gate usage during integration

`verify_authority.py strict` is task-scoped and expects a single task identity when protected paths are touched.

Do not describe strict as one aggregate multi-task wave assertion.

V2 should use:
- `strict` per candidate task branch/task,
- cumulative `anti-dup` on the evolving integration branch,
- full CI-equivalent validation between merges/waves,
- owner/Fable-only freeze at the final canonicalization point.

Do not let an integration branch grant itself authority.

### 6. Strengthen Wave 3 database validation

The three `db.py` PRs must remain sequential.

After each one, validate both:
- fresh bootstrap, and
- upgrade from a database created by the current `main` schema.

Explicitly include SQLite integrity and registry/health validation, using the existing CI `upgrade-from-main-schema` pattern.

### 7. Strengthen Wave 5 CLI convergence

The `cli.py` PRs remain sequential and must never be conflict-resolved as one combined batch.

After each merge:
- inspect the resulting CLI diff,
- detect duplicate command/parser registration or handler shadowing,
- run portability, compile, unit tests, and relevant CLI smoke validation,
- stop immediately if the current merge creates a regression.

Do not reorder the existing Wave 5 sequence unless concrete file-level dependency evidence justifies the change.

### 8. Findings file is review evidence, not canonical state

`.lucy/execution/CODEX_FINDINGS.md` may be append-only review evidence, but canonical failure state stays in the existing `errors` table.

The findings design should include:
- deterministic fingerprint / deduplication,
- task ID,
- expected vs observed,
- evidence reference,
- linked error ID where appropriate,
- review status controlled by planner/owner, not Codex.

Codex may propose changes in findings, but may never amend its own governing instructions.

### 9. Preserve current evidence semantics

Keep the existing invariant:
- executor output is not proof,
- exit code alone is not sufficient where the task requires stronger evidence,
- `validation_command` is independently rerun,
- model-only output without independent validation becomes review, not DONE.

Do not weaken any test or gate to simplify integration.

## Required V2 output

Keep it compact. Produce only:

1. **Corrections accepted / disagreements**
   - one short table showing which external-review corrections you accept,
   - any disagreement must cite concrete repo evidence.

2. **Revised integration waves**
   - preserve the current wave ordering unless file-overlap/dependency evidence requires a change,
   - state the validation checkpoint after each wave,
   - pay particular attention to Wave 3 `db.py`, Wave 5 `cli.py`, and Wave 6 `worker.py`.

3. **Codex work-order/result architecture**
   - canonical seven-field result contract,
   - mapping to existing task fields,
   - parser/rejection behavior,
   - independent validation behavior,
   - no new state store.

4. **Governance write-protection design**
   - what is enforceable today,
   - what must be added,
   - what remains unverified and requires owner decision.

5. **Findings/error loop**
   - reuse `errors.py`, `resume.py`, `AGENTS/{work_orders,results,prompts}`,
   - one append-only findings surface only,
   - no self-amending Codex.

6. **Autonomous Loop V2 delta**
   - changes to existing seams only,
   - how integration health, debugging, persistence, and bounded Codex fit into the existing loop,
   - no second scheduler/loop.

7. **Owner decisions only**
   - list only genuine policy/governance choices.

8. **Handoff to ChatGPT reviewer**
   - concise list of exactly what the next reviewer should verify and expand into Codex-ready repo instructions.

## Token discipline

Be terse and architectural.
Do not rewrite Part 0.
Do not repeat obvious invariants.
Do not dump code.
Do not implement anything.
Do not execute integration.
Do not create new tasks beyond those necessary to correct the roadmap architecture.

When complete, save the revised skeleton as a new planning file rather than overwriting the original draft, then stop.