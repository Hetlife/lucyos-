# M-CONTEXT-02 Architecture Decision — context at the worker boundary

**Status:** Fable-ratified candidate; protected owner merge pending; canonical
baseline unchanged

## Decision

Integrate the deterministic M-CONTEXT-01 compiler at the existing
`aion_core.worker` claim/execution boundary. Authorize FABLE-10 to change only
`aion_core/worker.py` for M-CONTEXT-02. Do not create a second scheduler,
queue, database, approval path, or execution service.

## Responsibility boundary

- `aion_core.recall.context_compiler` owns deterministic compilation, cache,
  budget, provenance, and redaction of derived task context.
- `aion_core.worker` already owns task claim and executor/model invocation. It
  must obtain and validate the compiled packet before changing the task to
  RUNNING or starting an executor.
- Canonical task, approval, session, error, security, and Resource Governor
  state remain in their existing AION modules.
- OpenClaw receives the owner/task work order plus the bounded derived context;
  raw history is not copied into the prompt.

## Failure and security policy

Context compilation or validation failure is fail-closed: the task becomes
BLOCKED, the claim is released, an existing AION error/session event is
recorded, and no worker starts. Markdown and JSON are both checked at the
worker trust boundary; task identity and source revision must match the
compiler result. Output paths must remain under the configured context root.

## Alternatives rejected

1. **Compile in OpenClaw routing:** would make OpenClaw a second policy owner
   and allow other AION executors to bypass context validation.
2. **Compile after worker start:** would permit uncontextualized side effects
   and violate fail-closed execution.
3. **Add a context daemon or scheduler:** duplicates existing task execution
   and introduces unnecessary always-on state.
4. **Persist context in a new database:** duplicates canonical AION state; the
   compiler's content-addressed files are derived and rebuildable.

## Scope, verification, and rollback

The protected implementation scope is exactly `aion_core/worker.py`; tests and
the architecture proposal are ordinary task artifacts. Required verification
includes fresh/cached builds, invalidation on task state and approvals,
project isolation, redaction, compilation-failure hold, focused integration
tests, the full suite, authority/anti-duplication, portability, security scan,
and architecture audit.

Rollback is the M-CONTEXT-02 implementation revert. The FABLE-10 override may
then be reverted separately if no descendant task depends on it. Main merge
and deployment remain separate owner gates.

## Ratification record

`HIGH_MODEL_BASELINE.json` adds exactly one task override:
`FABLE-10 -> aion_core/worker.py`. It does not change constitutional paths,
protected-path definitions, verifier logic, scanner exclusions, executor
scope, or any other task's authority.
