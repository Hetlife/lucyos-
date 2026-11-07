"""Auth-bound peer review audit events in the canonical AION DB, not a new state store."""
from copy import deepcopy

from aion_core import db, packets, tasks
from tests.base import AionTest
from tests.test_agent_harness import envelope
from tests.test_agent_collaboration import review


class PeerReviewDurabilityTest(AionTest):
    def setUp(self):
        super().setUp()
        self.task_id = tasks.create("Actual bounded LucyOS peer-review task",
                                    project="lucyos", success_criteria="verified evidence")
        self.proposal = envelope()
        self.proposal["task_id"] = self.task_id
        self.review = review("auditor-one", "CHALLENGE")
        self.review["task_id"] = self.task_id
        self.review["idempotency_key"] = "review-task-key-0001"

    def review_count(self):
        return db.connect().execute(
            "SELECT count(*) FROM events WHERE kind='agent.peer_review' AND subject=?",
            (self.task_id,)).fetchone()[0]

    def test_durable_evidence_and_exactly_once_replay(self):
        result = packets.record_authenticated_agent_review(
            self.proposal, self.review, authenticated_sender="auditor-one")
        self.assertEqual(result["status"], "RECORDED")
        self.assertEqual(result["triage"], "DISPUTED")
        self.assertFalse(result["task_pass_granted"])
        self.assertEqual(tasks.get(self.task_id)["status"], "READY")
        self.assertEqual(self.review_count(), 1)
        db.close()  # real new connection/session reading persisted SQLite
        self.assertEqual(self.review_count(), 1)
        again = packets.record_authenticated_agent_review(
            self.proposal, self.review, authenticated_sender="auditor-one")
        self.assertEqual(again["status"], "DUPLICATE")
        self.assertEqual(again["event_ref"], result["event_ref"])
        self.assertEqual(self.review_count(), 1)

    def test_spoofed_sender_is_rejected_without_state_change(self):
        with self.assertRaisesRegex(packets.PacketError, "authenticated"):
            packets.record_authenticated_agent_review(
                self.proposal, self.review, authenticated_sender="different-agent")
        self.assertEqual(self.review_count(), 0)

    def test_conflicting_replay_does_not_silently_replace_original(self):
        packets.record_authenticated_agent_review(
            self.proposal, self.review, authenticated_sender="auditor-one")
        forged = deepcopy(self.review)
        forged["review_issue"] = "Changed explanation after original replay."
        with self.assertRaisesRegex(packets.PacketError, "collision"):
            packets.record_authenticated_agent_review(
                self.proposal, forged, authenticated_sender="auditor-one")
        self.assertEqual(self.review_count(), 1)

    def test_duplicate_idempotency_key_with_different_message_id_is_denied(self):
        packets.record_authenticated_agent_review(
            self.proposal, self.review, authenticated_sender="auditor-one")
        forged = deepcopy(self.review)
        forged["message_id"] = "MSG-other-review"
        with self.assertRaisesRegex(packets.PacketError, "replay keys disagree"):
            packets.record_authenticated_agent_review(
                self.proposal, forged, authenticated_sender="auditor-one")
        self.assertEqual(self.review_count(), 1)

    def test_invalid_target_task_cannot_create_or_approve(self):
        unknown = deepcopy(self.proposal)
        unknown["task_id"] = "TASK-FAKE9999"
        badreview = deepcopy(self.review)
        badreview["task_id"] = "TASK-FAKE9999"
        with self.assertRaisesRegex(packets.PacketError, "canonical task"):
            packets.record_authenticated_agent_review(
                unknown, badreview, authenticated_sender="auditor-one")
        self.assertEqual(self.review_count(), 0)
