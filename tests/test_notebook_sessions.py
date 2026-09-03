import unittest

from tests.base import AionTest
from aion_core import config, db, errors, memory, notebook, resume, sessions, tasks


def append(text: str) -> None:
    notebook.ensure()
    with open(notebook.path(), "a", encoding="utf-8") as fh:
        fh.write("\n" + text.strip() + "\n")


class TestNotebook(AionTest):
    def test_bug_entry_creates_task_and_error(self):
        append("## [BUG] Status omits approval id\nfrom: het\nIt said none while A-101 was open.")
        result = notebook.sync()
        self.assertEqual(result["applied"], 1)
        self.assertTrue(any(t["title"].startswith("Fix:") for t in tasks.ready(10)))
        self.assertTrue(errors.open_errors())

    def test_template_examples_are_not_treated_as_entries(self):
        notebook.ensure()
        self.assertEqual(notebook.sync()["applied"], 0)

    def test_resync_is_a_no_op(self):
        append("## [TASK] Draft the outreach template\nfrom: chatgpt\nNeeds template approval.")
        first = notebook.sync()
        second = notebook.sync()
        self.assertEqual(first["applied"], 1)
        self.assertEqual(second["applied"], 0)
        self.assertEqual(len([t for t in tasks.ready(20)
                              if t["title"] == "Draft the outreach template"]), 1)

    def test_identical_entry_pasted_twice_is_deduplicated(self):
        entry = "## [FACT] Ollama is not installed yet\nfrom: openclaw\nChecked with ollama list."
        append(entry)
        notebook.sync()
        append(entry)
        result = notebook.sync()
        self.assertEqual(result["applied"], 0)
        self.assertEqual(result["skipped_duplicates"], 1)

    def test_secret_in_an_entry_is_stripped_from_disk_and_state(self):
        append("## [NOTE] key rotation\nfrom: het\n"
               "old token was ghp_AbCdEfGhIjKlMnOpQrStUvWxYz012345")
        result = notebook.sync()
        self.assertEqual(result["redacted"], 1)
        self.assertNotIn("ghp_AbCdEf", notebook.path().read_text())
        rows = db.connect().execute("SELECT body FROM notebook").fetchall()
        self.assertFalse(any("ghp_AbCdEf" in r["body"] for r in rows))

    def test_every_kind_produces_state(self):
        append("## [QUESTION] Should we use Razorpay or Stripe?\nfrom: het\nIndia only.")
        append("## [FIX] Bridge 429s\nfrom: openclaw\nThrottle to 20 messages a minute.")
        append("## [HANDOFF] Stopped mid-refactor\nfrom: claude\nResume at router.handle line 90.")
        notebook.sync()
        self.assertTrue(any(t["title"].startswith("Answer:") for t in tasks.ready(20)))
        self.assertTrue(memory.search("throttle"))
        self.assertIn("Stopped mid-refactor", db.get_meta("notebook_handoff"))

    def test_boot_syncs_the_notebook(self):
        append("## [TASK] Something from boot\nfrom: het\nbody")
        out = resume.boot()
        step = next(s for s in out["steps"] if s["step"] == "sync_notebook")
        self.assertIn("1 new entry", step["detail"])

    def test_unknown_author_is_recorded_not_rejected(self):
        append("## [NOTE] no author line here\nsomebody wrote this")
        notebook.sync()
        self.assertEqual(notebook.recent()[0]["author"], "unknown")


class TestSessions(AionTest):
    def test_full_session_lifecycle(self):
        sid = sessions.start("claude", model="claude-opus-5", model_class="C",
                             objective="design the approval flow")
        sessions.log(sid, "action", "read router.py and approvals.py")
        sessions.log(sid, "test", "ran 72 tests: all passed")
        summary = sessions.end(sid, outcome="approval flow designed and tested",
                               resume_point="wire the card into the bridge", spend_inr=42.5)
        self.assertEqual(summary["status"], "CLOSED")
        self.assertEqual(summary["spend_inr"], 42.5)
        log = (config.home() / "LOGS" / "sessions" / f"{sid}.md").read_text()
        self.assertIn("72 tests", log)
        self.assertIn("wire the card into the bridge", log)

    def test_index_is_written_for_cheap_reading(self):
        sid = sessions.start("openclaw", objective="nightly run")
        sessions.end(sid, outcome="all green", resume_point="none")
        index = (config.home() / "LOGS" / "SESSION_INDEX.md").read_text()
        self.assertIn(sid, index)
        self.assertIn("all green", index)

    def test_entries_are_capped_and_redacted(self):
        sid = sessions.start("openclaw")
        sessions.log(sid, "note", "token ghp_AbCdEfGhIjKlMnOpQrStUvWxYz012345 " + "x" * 900)
        log = (config.home() / "LOGS" / "sessions" / f"{sid}.md").read_text()
        self.assertNotIn("ghp_AbCdEf", log)
        self.assertLess(max(len(l) for l in log.splitlines()), 400)

    def test_open_sessions_are_visible(self):
        sid = sessions.start("ollama-local")
        self.assertIn(sid, [r["session_id"] for r in sessions.open_sessions()])
        sessions.end(sid, outcome="done")
        self.assertEqual(sessions.open_sessions(), [])

    def test_old_logs_compact_to_their_summary(self):
        sid = sessions.start("openclaw", objective="old work")
        for i in range(30):
            sessions.log(sid, "action", f"step {i} with a reasonably long description of work")
        sessions.end(sid, outcome="finished", resume_point="nothing pending")
        db.connect().execute("UPDATE sessions SET started_at='2020-01-01T00:00:00+00:00' "
                             "WHERE session_id=?", (sid,))
        db.connect().commit()
        self.assertEqual(sessions.compact_old(keep_days=30), 1)
        log = (config.home() / "LOGS" / "sessions" / f"{sid}.md").read_text()
        self.assertIn("compacted", log)
        self.assertIn("finished", log)
        self.assertNotIn("step 17", log)

    def test_logging_to_an_unknown_session_fails_loudly(self):
        with self.assertRaises(ValueError):
            sessions.log("SES-NOPE", "note", "x")


if __name__ == "__main__":
    unittest.main()
