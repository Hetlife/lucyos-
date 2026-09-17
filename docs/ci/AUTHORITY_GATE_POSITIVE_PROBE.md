# Authority gate positive probe

Purpose: prove the pull-request authority gate allows an ordinary, unprotected documentation change while evaluating the verifier from the base branch.

This file is intentionally outside protected paths and contains no architecture, security, approval, deployment, budget, or canonical-state changes.

Expected result: the `authority-gate` PR job runs its strict protected-path and anti-duplication checks and passes.
