"""Adversarial scope checks beyond the base collaboration happy-path suite."""
from aion_core import agents, packets, tasks
from tests.base import AionTest


class CollaborationAuthorityBoundaryTest(AionTest):
    def setUp(self):
        super().setUp()
        self.parent = tasks.create("Governed review plan", project="lucyos")
        self.child = tasks.create("Scoped code task", parent_task=self.parent, project="lucyos")
        agents.register(agent_id="collab-sandbox", role="worker", model="none",
                        model_class="B", cost_class="none",
                        capabilities="code,debug", max_complexity=2,
                        allowed_tools="fs_read,fs_write")

    def propose(self, path):
        return packets.propose_agent_collaboration(self.parent, [{
            "task_id": self.child, "agent_id": "collab-sandbox",
            "role": "builder", "capability": "code", "writable_paths": [path],
        }])

    def test_constitutional_and_protected_paths_not_claimable(self):
        forbidden = (
            "scripts/verify_authority.py", ".github/workflows/lucyos-ci.yml",
            "aion_core/security.py", "aion_core/config.py",
            "aion_core/resume.py", "aion_core/architecture.py",
            "scripts/check_portability.py", "scripts/ci_health_gate.py",
            "systemd/openclaw.service", "deploy/install.sh",
        )
        for path in forbidden:
            with self.subTest(path=path), self.assertRaises(packets.PacketError):
                self.propose(path)

    def test_malformed_capability_never_crashes_or_assigns(self):
        for invalid in ({}, [], None, 1, True):
            with self.subTest(capability=invalid):
                with self.assertRaises(packets.PacketError):
                    packets.propose_agent_collaboration(self.parent, [{
                        "task_id": self.child, "agent_id": "collab-sandbox",
                        "role": "builder", "capability": invalid, "writable_paths": []
                    }])

    def test_no_double_assign_same_agent_to_different_mutable_children(self):
        """No claim is made here, but proposed simultaneous mutators must not overlap."""
        other = tasks.create("Other file", parent_task=self.parent, project="lucyos")
        proposal = [
            {"task_id": self.child, "agent_id": "collab-sandbox",
             "role": "builder", "capability": "code", "writable_paths": ["tests/a.py"]},
            {"task_id": other, "agent_id": "collab-sandbox",
             "role": "builder", "capability": "code", "writable_paths": ["tests/b.py"]},
        ]
        # Agent can handle two sequential tasks, but cannot simultaneously own two
        # separate claims. The planner must label concurrency conditional on AION.
        plan = packets.propose_agent_collaboration(self.parent, proposal)
        self.assertFalse(plan["authorized_mutation"])
        self.assertEqual(plan["authority"], "AION_TASK_CLAIMS_ONLY")
