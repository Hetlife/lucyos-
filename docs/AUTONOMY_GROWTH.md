# LucyOS Autonomy Growth

Tags: `autonomy-growth` `iphone-first` `local-first` `token-efficiency` `memory` `supervision` `mac-ready`

Session: `SES-6CFFF673`
Base: `05c4f0ddff7e01f1aaccf7a1c927730e6977766a`

## Objective

Make LucyOS useful from an iPhone without routine terminal intervention. Every manual action should expose a concrete autonomy gap that can be removed safely later.

## Non-negotiable architecture

- Canonical operational memory stays in AION SQLite with provenance and FTS.
- Semantic/vector recall is a derived, rebuildable index; it never becomes canonical state.
- Deterministic retrieval is first. Local embeddings are second. Local LLM reasoning is third. Cloud models are last.
- A local model may extract, summarize, compact, classify, or rerank memories; it does not own the database.
- Reuse the existing task queue, approval engine, health checks, resource governor, sessions, errors and checkpoint/resume state.
- Do not add a second scheduler, approval system, secret store, global queue, or always-on reasoning loop.
## Existing mechanisms to preserve

- `aion_core/memory.py`: SQLite/FTS durable memory with confidence and provenance.
- `aion_core/semantic_recall.py`: optional rebuildable sqlite-vec semantic index.
- `aion_core/sessions.py`: compact per-session logs and 30-day compaction.
- `aion_core/resume.py`: restart-safe checkpoint and exact resume point.
- `aion_core/errors.py`: failure classification, root cause, fix and lessons.
- `aion_core/worker.py`: bounded autonomous execution and anti-loop escalation.
- `aion_core/governor.py`: model-spend/resource downshift policy.
- `scripts/build_loop.sh`: recurring queue execution under the canonical timer.
- `scripts/maintenance.sh`: backup/restore-test, LearnRepo, secret scan and deep health.

## Required supervision loop

1. Measure live health and Git cleanliness.
2. Read queue, approvals, unresolved errors, checkpoint and open sessions.
3. Surface the single current bottleneck and exact next action.
4. Prefer DET; then local model; then bounded cloud model only when justified.
5. Require evidence before DONE; stale executor text is never completion evidence.
6. After a failure, record root cause/fix/lesson before retrying materially different work.
7. After two materially different failures, escalate instead of looping.
8. Checkpoint at meaningful milestones and compact old logs automatically.
## Future Apple Silicon memory/runtime design

Use the cheapest layer that answers the question correctly:

1. SQLite/FTS for exact facts, IDs, task state, decisions and recent history.
2. Local embedding search only when lexical recall is insufficient.
3. A small resident local model for memory extraction/compaction/reranking and simple agent work.
4. A larger local model loaded on demand for bounded reasoning/coding.
5. ChatGPT/other strong cloud models only for work that exceeds local capability.

The Mac runtime must sit behind LucyOS model routing so changing Ollama/MLX/llama.cpp does not change AION state or agent contracts. Benchmark actual quality, latency, memory and power before selecting a default model.

## Acceptance gates

- iPhone -> ChatGPT -> LucyOS node -> AION -> executor -> evidence -> canonical state works end-to-end.
- Restart/reboot does not lose task, session, checkpoint or failure state.
- Duplicate execution attempts are prevented by the existing claim/singleton controls.
- A completed task cannot be marked DONE without verifiable evidence.
- Routine recall does not require paid model tokens.
- Health supervision makes zero LLM calls by default.
- Git/security/test failures produce evidence and a bounded repair plan, not an infinite retry loop.
- Scaling to a Mac or additional nodes does not create a second source of truth.

## Deferred until evidence justifies it

- Qdrant or another network vector database. SQLite/FTS + derived local vectors are preferred first.
- Always-on LLM supervision. Deterministic timers/watchdogs are preferred.
- Automatic merge or production exposure without the existing approval/evidence gates.
