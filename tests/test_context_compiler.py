import json
import os
import sqlite3
import tempfile
from pathlib import Path

from tests.base import AionTest
from aion_core import approvals, db, memory, sessions, tasks
from aion_core.recall import context_compiler


class ContextCompilerTest(AionTest):
    def _seed(self):
        task = tasks.create(
            "Review Lucy-den context memory architecture",
            project="LucyOS", status="READY", priority=1,
            description="Keep local context compact and secure",
            blockers="", next_action="compile a bounded pack",
            success_criteria="deterministic derived context")
        tasks.create("Unrelated customer UI", project="OtherProject", status="READY")
        sid = sessions.start("codex", objective="Test context compiler on Lucy-den")
        sessions.log(sid, "decision", "Reuse canonical AION sessions and tasks")
        sessions.end(sid, outcome="Context source verified", tasks_touched=task,
                     resume_point="Build deterministic projections")
        memory.remember("decision", "Context remains derived", "Do not create a second database",
                        project="LucyOS", confidence="VERIFIED_FACT", source=sid,
                        tags="architecture context-memory")
        approvals.create("Merge context compiler to main", project="LucyOS",
                         why="Main is protected", owner_action="Review exact SHA")
        return task

    def _compile(self, task, out, budget=context_compiler.DEFAULT_BUDGET_BYTES):
        return context_compiler.compile_context(
            repo=Path(__file__).resolve().parents[1], task_id=task,
            output_root=out, budget_bytes=budget)

    def test_real_sources_projections_budget_and_project_isolation(self):
        task = self._seed()
        out = self.tmp / "derived"
        result = self._compile(task, out)
        self.assertEqual(result["status"], "BUILT")
        self.assertLessEqual(result["bytes"]["markdown"], context_compiler.DEFAULT_BUDGET_BYTES)
        self.assertLessEqual(result["bytes"]["json"], context_compiler.DEFAULT_BUDGET_BYTES)
        packet = json.loads((out / "current" / "CURRENT_CONTEXT.json").read_text())
        self.assertEqual(packet["task_id"], task)
        self.assertTrue(packet["owner_gates"])
        self.assertTrue(all(x["project"] == "LucyOS" or x["kind"] == "repository"
                            for x in packet["selected"]))
        self.assertNotIn("Unrelated customer UI", (out / "current" / "CURRENT_CONTEXT.md").read_text())
        self.assertTrue((out / "topics" / "context-memory.md").is_file())
        self.assertTrue(all((out / "topics" / f"{topic}.md").is_file()
                            for topic in context_compiler.TOPIC_KEYWORDS))
        self.assertTrue((out / "projects" / "lucyos" / "PROJECT_SUMMARY.md").is_file())
        self.assertTrue((out / "sessions" / "summaries" / f"{sessions.index(1)[0]['session_id']}.md").is_file())
        self.assertTrue(all(x["provenance"] for x in packet["selected"]))

    def test_incremental_cache_is_deterministic_and_does_not_mutate_db(self):
        task = self._seed()
        out = self.tmp / "derived"
        before = self._db_snapshot()
        first = self._compile(task, out)
        md = (out / "current" / "CURRENT_CONTEXT.md").read_bytes()
        js = (out / "current" / "CURRENT_CONTEXT.json").read_bytes()
        mtimes = [(out / "current" / name).stat().st_mtime_ns
                  for name in ("CURRENT_CONTEXT.md", "CURRENT_CONTEXT.json")]
        second = self._compile(task, out)
        self.assertEqual(second["status"], "CACHE_HIT")
        self.assertEqual(second["cache"], {"hits": second["source_count"], "misses": 0})
        self.assertEqual(md, (out / "current" / "CURRENT_CONTEXT.md").read_bytes())
        self.assertEqual(js, (out / "current" / "CURRENT_CONTEXT.json").read_bytes())
        self.assertEqual(mtimes, [(out / "current" / name).stat().st_mtime_ns
                                  for name in ("CURRENT_CONTEXT.md", "CURRENT_CONTEXT.json")])
        self.assertEqual(before, self._db_snapshot())
        self.assertGreater(first["cache"]["misses"], 0)

    def test_sensitive_source_is_redacted_and_output_scans_clean(self):
        task = self._seed()
        conn = db.connect()
        marker = "A" * 26
        secret = "sk-" + "proj-" + marker
        conn.execute("UPDATE tasks SET description=? WHERE task_id=?",
                     ("OpenAI key " + secret, task))
        conn.commit()
        out = self.tmp / "derived"
        result = self._compile(task, out)
        all_text = (out / "current" / "CURRENT_CONTEXT.md").read_text() + \
                   (out / "current" / "CURRENT_CONTEXT.json").read_text()
        self.assertNotIn(marker, all_text)
        self.assertIn("[REDACTED]", all_text)
        self.assertGreater(result["rejected_sensitive_items"], 0)

    def test_budget_and_corrupt_cache_rebuild(self):
        task = self._seed()
        for i in range(40):
            memory.remember("research", f"Context evidence {i}", "bounded evidence " * 80,
                            project="LucyOS", source=f"fixture-{i}")
        out = self.tmp / "derived"
        result = self._compile(task, out, budget=context_compiler.MIN_BUDGET_BYTES)
        self.assertLessEqual(result["bytes"]["markdown"], context_compiler.MIN_BUDGET_BYTES)
        self.assertLessEqual(result["bytes"]["json"], context_compiler.MIN_BUDGET_BYTES)
        (out / "current" / "MANIFEST.json").write_text("{broken")
        rebuilt = self._compile(task, out, budget=context_compiler.MIN_BUDGET_BYTES)
        self.assertEqual(rebuilt["status"], "BUILT")

    def test_missing_or_corrupt_canonical_database_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            missing = Path(td) / "missing.sqlite3"
            with self.assertRaises(context_compiler.ContextCompilerError):
                context_compiler.compile_context(repo=Path(td), output_root=Path(td) / "out",
                                                 db_path=missing)
            corrupt = Path(td) / "bad.sqlite3"
            corrupt.write_text("not sqlite")
            with self.assertRaises(context_compiler.ContextCompilerError):
                context_compiler.compile_context(repo=Path(td), output_root=Path(td) / "out",
                                                 db_path=corrupt)

    def test_topic_router_supports_required_topics(self):
        samples = {
            "architecture": "canonical architecture",
            "ui-ux": "UI design",
            "infrastructure": "service unit infrastructure",
            "security-privacy": "security privacy",
            "context-memory": "context memory",
            "automation": "automation supervisor",
            "deployment": "production deployment",
            "testing": "regression testing",
            "mobile-owner-console": "WhatsApp mobile owner console",
            "lucynest": "LucyNest touchscreen",
            "mark-2": "Mark-2 droplet",
            "lucy-den": "Lucy-den local node",
            "learnrepo": "LearnRepo candidate repo",
            "business": "business revenue",
        }
        for topic, text in samples.items():
            self.assertIn(topic, context_compiler._topics(text))

    def _db_snapshot(self):
        conn = db.connect()
        return {table: conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                for table in ("tasks", "sessions", "approvals", "errors", "memory", "events")}


if __name__ == "__main__":
    import unittest
    unittest.main()
