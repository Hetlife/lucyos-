"""TR-1-08: a session log recorded under another home must not block task execution.

Session rows store an absolute log path. After `aion import` from another host or user
(for example `/root/openclaw/shared_brain/...` from Mark-2 onto a machine whose brain is
under `/home/<user>/...`) that path is absent or unreadable. The compiler used to treat
that as fatal, which blocked every task before it ran (ISSUE-040).
"""
import os
import stat
import unittest
from pathlib import Path

from tests.base import AionTest
from aion_core import db, sessions, tasks
from aion_core.recall import context_compiler

FOREIGN = "/nonexistent-root/openclaw/shared_brain/LOGS/sessions/"
REPO = Path(__file__).resolve().parents[1]


class SessionLogPathTest(AionTest):
    def _session(self, entry="Reuse canonical AION sessions"):
        sid = sessions.start("codex", objective="foreign path test")
        sessions.log(sid, "decision", entry)
        sessions.end(sid, outcome="done", resume_point="none")
        return sid

    def _rewrite_path(self, sid, recorded):
        conn = db.connect()
        conn.execute("UPDATE sessions SET log_path=? WHERE session_id=?", (recorded, sid))
        conn.commit()

    def _compile(self, task_id):
        return context_compiler.compile_context(
            repo=REPO, task_id=task_id, output_root=self.tmp / "derived")

    def test_compile_survives_a_session_log_recorded_under_another_home(self):
        sid = self._session()
        task = tasks.create("any task", project="LucyOS", status="READY")
        (sessions.log_dir() / f"{sid}.md").unlink()  # the imported brain has no such file
        self._rewrite_path(sid, FOREIGN + f"{sid}.md")
        result = self._compile(task)
        self.assertEqual(result["status"], "BUILT")
        self.assertEqual(result["unavailable_sources"], 1)

    def test_log_is_found_by_name_inside_this_brain(self):
        sid = self._session("A decision that must reach the excerpt")
        self._rewrite_path(sid, FOREIGN + f"{sid}.md")  # the real copy still sits in this brain
        text = sessions.read_log(FOREIGN + f"{sid}.md")
        self.assertIn("A decision that must reach the excerpt", text)
        metrics = {"rejected_sensitive_items": 0}
        excerpt, _ = context_compiler._session_log_excerpt(FOREIGN + f"{sid}.md", metrics)
        self.assertIn("A decision that must reach the excerpt", excerpt)
        self.assertNotIn("unavailable_sources", metrics)

    def test_a_missing_log_is_unavailable_not_fatal_and_hash_is_stable(self):
        metrics = {"rejected_sensitive_items": 0}
        first = context_compiler._session_log_excerpt(FOREIGN + "SES-GONE.md", metrics)
        second = context_compiler._session_log_excerpt(FOREIGN + "SES-GONE.md", {})
        self.assertEqual(first[0], "")
        self.assertEqual(first[1], second[1])
        self.assertEqual(metrics["unavailable_sources"], 1)

    def test_only_files_inside_this_brains_log_directory_are_ever_read(self):
        canary = self.tmp / "outside-the-log-dir.md"
        canary.write_text("| 00:00 | decision | SECRET-CANARY |\n")
        for recorded in (str(canary), "../../etc/passwd", "/etc/passwd", "..", "", "/"):
            self.assertIsNone(sessions.read_log(recorded), recorded)
        self.assertNotIn("SECRET-CANARY",
                         context_compiler._session_log_excerpt(str(canary), {})[0])

    @unittest.skipIf(os.geteuid() == 0, "directory permissions do not stop root")
    def test_an_unreadable_log_directory_does_not_raise(self):
        sid = self._session()
        log_dir = sessions.log_dir()
        mode = log_dir.stat().st_mode
        log_dir.chmod(0)
        self.addCleanup(log_dir.chmod, stat.S_IMODE(mode))
        self.assertIsNone(sessions.read_log(str(log_dir / f"{sid}.md")))
        context_compiler._session_log_excerpt(str(log_dir / f"{sid}.md"), {})

    def test_writes_for_a_foreign_recorded_path_land_in_this_brain(self):
        sid = self._session()
        self._rewrite_path(sid, FOREIGN + f"{sid}.md")
        sessions.log(sid, "note", "written after the move")
        self.assertIn("written after the move",
                      (sessions.log_dir() / f"{sid}.md").read_text())

    def test_compact_old_never_touches_a_path_outside_the_brain(self):
        outside = self.tmp / "keep-me.md"
        outside.write_text("x" * 600)
        sid = self._session()
        self._rewrite_path(sid, str(outside))
        conn = db.connect()
        conn.execute("UPDATE sessions SET started_at='2000-01-01T00:00:00+00:00' "
                     "WHERE session_id=?", (sid,))
        conn.commit()
        sessions.compact_old(keep_days=1)
        self.assertEqual(outside.read_text(), "x" * 600)


if __name__ == "__main__":
    unittest.main()
