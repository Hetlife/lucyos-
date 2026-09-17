"""Upgrade-from-old-state tests.

Owner rule: every schema/enum/policy migration in LucyOS ships an
upgrade-from-old-state test here. A clean-database test suite cannot see a
migration bug that only exists on a database carrying rows written by older
code -- that gap is exactly how the f0/F0 skill-registry bug went unnoticed.
"""
from aion_core import db, skills
from tests.base import AionTest


class TestUpgradeFromOldState(AionTest):
    def test_legacy_lowercase_f0_heals(self):
        skills.ensure_defaults()
        conn = db.connect()
        conn.execute("UPDATE skills SET cost_class='f0' WHERE skill_id='ai.local'")
        conn.commit()
        self.assertEqual(skills.get("ai.local")["cost_class"], "f0")

        skills.ensure_defaults()

        self.assertEqual(skills.get("ai.local")["cost_class"], "F0")
        self.assertEqual(skills.validate_registry(), [])

    def test_all_four_columns_lowercase_across_different_skills_heal(self):
        skills.ensure_defaults()
        conn = db.connect()
        conn.execute("UPDATE skills SET cost_class='e1' WHERE skill_id='ai.cloud'")
        conn.execute("UPDATE skills SET risk_class='r1' WHERE skill_id='core.state'")
        conn.execute("UPDATE skills SET data_class='internal' WHERE skill_id='core.health'")
        conn.execute("UPDATE skills SET priority='p1' WHERE skill_id='core.tasks'")
        conn.commit()
        self.assertEqual(skills.validate_registry(),
                         ['ai.cloud:invalid-cost', 'core.health:invalid-data',
                          'core.state:invalid-risk', 'core.tasks:invalid-priority'])

        skills.ensure_defaults()

        self.assertEqual(skills.validate_registry(), [])
        self.assertEqual(skills.get("ai.cloud")["cost_class"], "E1")
        self.assertEqual(skills.get("core.state")["risk_class"], "R1")
        self.assertEqual(skills.get("core.health")["data_class"], "INTERNAL")
        self.assertEqual(skills.get("core.tasks")["priority"], "P1")

    def test_ensure_defaults_is_idempotent(self):
        skills.ensure_defaults()
        conn = db.connect()
        conn.execute("UPDATE skills SET cost_class='e0' WHERE skill_id='ai.cloud'")
        conn.commit()
        skills.ensure_defaults()
        first = [dict(r) for r in skills.all_skills()]

        skills.ensure_defaults()
        second = [dict(r) for r in skills.all_skills()]

        self.assertEqual(first, second)


if __name__ == "__main__":
    import unittest
    unittest.main()
