"""AION-backed collaboration proposals and fail-closed AI disputes."""
from copy import deepcopy

from aion_core import agents, packets, tasks
from tests.base import AionTest
from tests.test_agent_harness import envelope


def review(sender="reviewer-one", position="SUPPORT", target="MSG-001"):
    value = envelope()
    value.update(message_id="REVIEW-" + sender, sender=sender, recipient="aion-review",
                 type="REVIEW", status="VERIFYING", review_target=target,
                 review_position=position, evidence_refs=["evidence/review-" + sender],
                 changed_paths=[], tests=[{"command": "python3 -m unittest tests.test_agent_harness",
                                            "status": "PASS", "evidence_ref": "evidence/review-tests"}])
    if position == "CHALLENGE":
        value["review_issue"] = "Counterexample: the verifier must reject missing evidence."
    return value


class CollaborationTest(AionTest):
    def setUp(self):
        super().setUp()
        self.parent = tasks.create("Build safe agent collaboration", project="lucyos",
                                   success_criteria="independently accepted result")
        self.child_a = tasks.create("Backend bounded fix", parent_task=self.parent, project="lucyos")
        self.child_b = tasks.create("Independent audit", parent_task=self.parent, project="lucyos")
        self.child_c = tasks.create("Second bounded fix", parent_task=self.parent, project="lucyos")
        agents.register(agent_id="builder-verified-registry", role="worker", model="no-runtime",
                        model_class="B", cost_class="low", capabilities="code,debug",
                        max_complexity=3, allowed_tools="fs")
        agents.register(agent_id="reviewer-verified-registry", role="reviewer", model="no-runtime",
                        model_class="C", cost_class="high",
                        capabilities="security_review,code", max_complexity=5,
                        allowed_tools="fs_read")

    def spec(self, task, agent="builder-verified-registry", role="builder",
             capability="code", paths=None):
        return {"task_id": task, "agent_id": agent, "role": role,
                "capability": capability,
                "writable_paths": ["tests/test_agent_collaboration.py"] if paths is None else paths}

    def test_can_parallelize_disjoint_build_and_read_only_review(self):
        options = [
            self.spec(self.child_a),
            self.spec(self.child_b, "reviewer-verified-registry", "reviewer",
                      "security_review", []),
            self.spec(self.child_c, paths=["tests/test_agent_harness.py"]),
        ]
        plan = packets.propose_agent_collaboration(self.parent, options)
        self.assertEqual(len(plan["assignment_proposals"]), 3)
        self.assertFalse(plan["authorized_mutation"])
        self.assertEqual(plan["assignment_proposals"][1]["capability_status"],
                         "REGISTERED_NOT_LIVE_VERIFIED")
        self.assertEqual(tasks.get(self.child_a)["status"], "READY")

    def test_same_file_mutators_cannot_be_concurrent(self):
        with self.assertRaisesRegex(packets.PacketError, "overlapping"):
            packets.propose_agent_collaboration(
                self.parent, [self.spec(self.child_a), self.spec(self.child_c)])
        with self.assertRaisesRegex(packets.PacketError, "overlapping"):
            packets.propose_agent_collaboration(
                self.parent, [self.spec(self.child_a, paths=["tests/unit"]),
                              self.spec(self.child_c, paths=["tests/unit/test_case.py"])])

    def test_reviewer_never_gets_mutation_scope(self):
        with self.assertRaisesRegex(packets.PacketError, "read-only"):
            packets.propose_agent_collaboration(
                self.parent, [self.spec(self.child_b, "reviewer-verified-registry",
                                        "reviewer", "security_review")])

    def test_unregistered_capability_and_unknown_task_denied(self):
        bad = self.spec(self.child_a, capability="security_review")
        with self.assertRaisesRegex(packets.PacketError, "lacks"):
            packets.propose_agent_collaboration(self.parent, [bad])
        bad["task_id"] = "TASK-NOT-FOUND"
        with self.assertRaises(packets.PacketError):
            packets.propose_agent_collaboration(self.parent, [bad])

    def test_protected_or_broad_mutations_denied(self):
        for path in ("aion_core/db.py", ".lucy/authority/X.md",
                     "../relative.py", "/tmp/exploit", "docs", "tests",
                     "aion_core/worker.py"):
            with self.subTest(path=path), self.assertRaises(packets.PacketError):
                packets.propose_agent_collaboration(
                    self.parent, [self.spec(self.child_a, paths=[path])])

    def test_agent_ranking_requires_actual_reliability_history(self):
        agents.register(agent_id="cheap-proven", role="worker", model="synthetic",
                        model_class="B", cost_class="low", capabilities="code",
                        max_complexity=3, allowed_tools="fs", runs=12,
                        failures=1, reliability=0.917)
        agents.register(agent_id="fast-but-unproven", role="worker", model="synthetic",
                        model_class="B", cost_class="none", capabilities="code",
                        max_complexity=3, allowed_tools="fs", runs=0,
                        reliability=1.0)
        ranked = packets.rank_agent_candidates("code")
        names = [r["agent_id"] for r in ranked["candidates"]]
        self.assertLess(names.index("cheap-proven"), names.index("fast-but-unproven"))
        entry = next(r for r in ranked["candidates"] if r["agent_id"] == "fast-but-unproven")
        self.assertEqual(entry["candidate_status"], "INSUFFICIENT_HISTORY")
        self.assertIsNone(entry["recorded_reliability"])
        self.assertFalse(ranked["authorized_dispatch"])
        self.assertTrue(all(r["live_provider_health"] == "UNKNOWN"
                            for r in ranked["candidates"]))

    def test_agent_ranking_rejects_unjustified_threshold(self):
        with self.assertRaises(packets.PacketError):
            packets.rank_agent_candidates("code", min_reliability=1.2)

    def test_unrelated_child_rejected(self):
        other = tasks.create("Wrong parent", project="lucyos")
        with self.assertRaisesRegex(packets.PacketError, "child"):
            packets.propose_agent_collaboration(
                self.parent, [self.spec(other)])


class DisputeTest(AionTest):
    def test_support_never_means_pass(self):
        decision = packets.adjudicate_agent_reviews(envelope(), [review()])
        self.assertEqual(decision["state"], "AGREED_PENDING_VERIFICATION")
        self.assertFalse(decision["task_pass_granted"])
        self.assertFalse(decision["owner_approval_granted"])

    def test_conflict_requires_test_not_majority_vote(self):
        decision = packets.adjudicate_agent_reviews(
            envelope(), [review(), review("reviewer-two", "CHALLENGE"),
                         review("reviewer-three", "SUPPORT")])
        self.assertEqual(decision["state"], "DISPUTED")
        self.assertIn("deterministic test", decision["next_action"])
        self.assertFalse(decision["authorized_mutation"])

    def test_duplicate_or_self_review_is_rejected(self):
        with self.assertRaisesRegex(packets.PacketError, "distinct"):
            packets.adjudicate_agent_reviews(envelope(), [review(), review()])
        with self.assertRaisesRegex(packets.PacketError, "distinct"):
            packets.adjudicate_agent_reviews(envelope(), [review("cheap-worker")])

    def test_wrong_baseline_or_task_is_rejected(self):
        for update in ({"task_id": "TASK-ABCDEF12"}, {"baseline_ref": "old-sha"},
                       {"review_target": "OTHER-MSG"}):
            r = review()
            r.update(update)
            with self.subTest(update=update), self.assertRaises(packets.PacketError):
                packets.adjudicate_agent_reviews(envelope(), [r])

    def test_no_reviews_pending_and_uncertainty_escalates(self):
        self.assertEqual(packets.adjudicate_agent_reviews(envelope(), [])["state"],
                         "PENDING_INDEPENDENT_REVIEW")
        self.assertEqual(
            packets.adjudicate_agent_reviews(envelope(),
                [review(position="UNCERTAIN")])["state"], "INCONCLUSIVE")

    def test_challenge_requires_reason_and_evidence(self):
        r = review(position="CHALLENGE")
        del r["review_issue"]
        with self.assertRaises(packets.PacketError):
            packets.adjudicate_agent_reviews(envelope(), [r])
        r = review(position="CHALLENGE")
        r["evidence_refs"] = []
        with self.assertRaises(packets.PacketError):
            packets.adjudicate_agent_reviews(envelope(), [r])
