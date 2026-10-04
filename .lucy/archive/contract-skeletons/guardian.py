"""Deployment guardian: contract C5's pipeline as a deterministic state
machine that cannot deploy.

This module never runs a deploy, restarts a service, or makes a network
call.  It only tracks whether the twelve mandatory stages were completed,
in order, with real evidence at each one.  Autonomous deployment stays
disabled at the module level until an owner flips ENABLED -- flipping it
is not something this module can do to itself.
"""
from __future__ import annotations

from . import util

# Autonomous LIMITED DEPLOY is refused entirely while this is False.  The
# owner enables it; nothing in this module ever sets it to True.
ENABLED = False

STAGES = (
    "SNAPSHOT", "ISOLATE", "IMPLEMENT", "TEST", "STATIC_SECURITY",
    "INDEPENDENT_VERIFY", "STAGE", "HEALTH_CHECK", "LIMITED_DEPLOY",
    "MONITOR", "AUTO_ROLLBACK", "EVIDENCE",
)

PENDING, IN_PROGRESS, ROLLED_BACK, COMPLETE = "PENDING", "IN_PROGRESS", "ROLLED_BACK", "COMPLETE"


class GuardianError(Exception):
    pass


class Pipeline:
    """One deployment attempt's evidence trail.  A rolled-back pipeline is
    dead: start a fresh one rather than retrying the same instance, so a
    rollback can never be quietly overwritten by a later advance()."""

    def __init__(self, deployment_id: str):
        self.deployment_id = deployment_id
        self.stage_index = -1
        self.evidence: dict[str, dict] = {}
        self.status = PENDING

    def current_stage(self) -> str | None:
        return STAGES[self.stage_index] if self.stage_index >= 0 else None

    def advance(self, stage: str, evidence: dict) -> str:
        """Move to `stage`, which must be exactly the next stage in order,
        and record `evidence` for it.  A process exit code is never proof:
        evidence must be a non-empty dict describing an asserted, independently
        re-read state change, not a boolean success flag alone."""
        if self.status == ROLLED_BACK:
            raise GuardianError(
                f"{self.deployment_id}: pipeline was rolled back at "
                f"{self.evidence.get('AUTO_ROLLBACK', {}).get('at_stage')!r}; "
                "a fresh Pipeline is required, this one cannot resume"
            )
        if self.status == COMPLETE:
            raise GuardianError(f"{self.deployment_id}: pipeline already complete")

        expected_index = self.stage_index + 1
        if expected_index >= len(STAGES):
            raise GuardianError(f"{self.deployment_id}: no further stage to advance to")
        expected = STAGES[expected_index]
        if stage != expected:
            raise GuardianError(
                f"{self.deployment_id}: cannot advance to {stage!r}; "
                f"next required stage is {expected!r} -- stages cannot be skipped"
            )
        if not evidence or not isinstance(evidence, dict):
            raise GuardianError(
                f"{self.deployment_id}: {stage} requires real evidence "
                "(a non-empty dict); an exit code alone is never proof"
            )
        if stage == "LIMITED_DEPLOY" and not ENABLED:
            raise GuardianError(
                f"{self.deployment_id}: LIMITED_DEPLOY refused -- "
                "aion_core.guardian.ENABLED is False"
            )

        self.evidence[stage] = dict(evidence)
        self.stage_index = expected_index
        self.status = COMPLETE if expected == STAGES[-1] else IN_PROGRESS
        return expected

    def rollback(self, reason: str) -> None:
        """Halt the pipeline permanently.  Never a scheduled sweep, never
        automatic retry -- the caller decides a failure happened and this
        just records it and closes the pipeline off from further advance()."""
        if self.status in (ROLLED_BACK, COMPLETE):
            raise GuardianError(
                f"{self.deployment_id}: cannot roll back a pipeline already {self.status}"
            )
        self.evidence["AUTO_ROLLBACK"] = {
            "reason": reason,
            "at_stage": self.current_stage(),
            "rolled_back_at": util.now(),
        }
        self.status = ROLLED_BACK
