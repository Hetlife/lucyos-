"""S-30: keep every bounded worker on one compact result-packet contract."""
from pathlib import Path
import io
import json
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch

from tests.base import AionTest
from aion_core import context, tasks


FIELDS = ("STATUS", "ACTIONS", "FILES_CHANGED", "TESTS", "RESULTS", "BLOCKERS", "NEXT_ACTION")
LEGACY = ("ACTIONS_TAKEN", "TESTS_RUN", "FAILURES / RISKS / ASSUMPTIONS", "NEXT_RECOMMENDED_ACTION", "EXACT_RESUME_POINT")


class ContextResultContractTest(AionTest):
    def test_context_packet_uses_only_canonical_worker_fields(self):
        task_id = tasks.create("contract smoke", success_criteria="packet names are stable")
        packet = context.build(task_id)
        contract_line = next(line for line in packet.splitlines() if line.startswith("STATUS / ACTIONS /"))
        self.assertEqual(contract_line.split(" / "), list(FIELDS))
        for legacy in LEGACY:
            self.assertNotIn(legacy, packet)

    def test_codex_wrapper_declares_same_contract(self):
        script = (Path(__file__).resolve().parents[1] / "scripts" / "aion_codex_worker.sh").read_text()
        expected = ", ".join(FIELDS)
        self.assertIn(f"Return a compact result packet with: {expected}.", script)


class RepoContextTest(AionTest):
    def setUp(self):
        super().setUp()
        self.task = tasks.create("context regression", success_criteria="stable output")

    def test_default_bytes_match_original(self):
        expected = """# WORK ORDER {task_id}

TASK_ID: {task_id}
OBJECTIVE: context regression
WHY IT MATTERS: not recorded
PROJECT: default
STATUS: READY   PRIORITY: 3   VALUE: 2.1
ASSIGNED CLASS: B (router suggests C: complexity 4 exceeds cheap-model reliability)

## CURRENT STATE
not recorded
Bottleneck: not identified

## FILES
not specified

## SUCCESS CRITERIA
stable output

## VALIDATION METHOD
run the repo test suite and record the command + result

## CONSTRAINTS
- Do not mark DONE without evidence (a command run, a measurement, an observation).
- Never write a credential into shared state, git, logs or WhatsApp.
- Tier-3 actions (spend, contracts, credentials, irreversible changes) need an approval id.
- Escalate after two materially different failures instead of looping.

## RELEVANT MEMORY
- none

## RECENT FAILURES
- none

## RETURN THIS RESULT PACKET

STATUS / ACTIONS / FILES_CHANGED / TESTS / RESULTS / BLOCKERS / NEXT_ACTION
Use these seven field names exactly. Put unresolved failures in BLOCKERS; put the exact resume step in NEXT_ACTION. Do not add alternate field names.
""".format(task_id=self.task)
        self.assertEqual(context.build(self.task).encode(), expected.encode())
        with patch.object(context, "_repo_sections", side_effect=AssertionError("repo read")):
            self.assertEqual(json.loads(context.build(self.task, json_output=True))["context"],
                             context.build(self.task))

    def test_sections_budget_and_hashes(self):
        packet = context.build(self.task, module="kernel.tasks")
        headings = ["## FILES", "## MODULE kernel.tasks", "## OWNED FILES", "## TESTS",
                    "## NEIGHBOURS", "## DELTA SINCE", "## EXCLUDED", "## CANONICAL",
                    "## ROLLBACK / COMMANDS", "## SUCCESS CRITERIA"]
        positions = [packet.index(h) for h in headings]
        self.assertEqual(positions, sorted(positions))
        owned = packet.split("## OWNED FILES")[1].split("## TESTS")[0]
        self.assertLessEqual(owned.count("sha256"), 10)
        self.assertIn("sha256 " + context.util.sha256_file(Path(context.__file__).parent / "tasks.py")[:12], owned)
        self.assertIn("tests/test_context_contract.py", packet)
        empty = context.build(self.task, module="kernel.tasks", budget_bytes=0)
        self.assertIn("Selected 0 files / 0 bytes", empty)
        self.assertIn("aion_core/tasks.py (budget exceeded; path only, no content)", empty)
        self.assertNotIn("def create(", packet)

    def test_hard_file_and_byte_caps(self):
        packet = context.build(self.task, module="governance", budget_bytes=10**9)
        owned = packet.split("## OWNED FILES")[1].split("## TESTS")[0]
        self.assertLessEqual(owned.count("sha256"), 10)
        self.assertIn("limit 10 / 204800", owned)
        self.assertIn("budget exceeded; path only, no content", packet)
        size = (Path(context.__file__).parent / "approvals.py").stat().st_size
        packet = context.build(self.task, module="kernel.tasks", budget_bytes=size)
        self.assertIn(f"Selected 1 files / {size} bytes", packet)

    def test_git_failures_are_safe(self):
        with patch.object(context.subprocess, "run", side_effect=context.subprocess.TimeoutExpired("git", 10)):
            with self.assertRaisesRegex(ValueError, "timed out"):
                context.build(self.task, module="kernel.tasks")

    def test_delta_explicit_and_stored_watermark(self):
        real_git = context._git
        def git(repo, *args):
            if args[0] == "diff":
                return "aion_core/tasks.py\0aion_core/memory.py\0"
            return real_git(repo, *args)
        with patch.object(context, "_git", side_effect=git):
            context.db.set_meta("last_high_model_reviewed_commit", "HEAD")
            for kwargs in ({}, {"since": "HEAD"}):
                packet = context.build(self.task, module="kernel.tasks", **kwargs)
                delta = packet.split("## DELTA SINCE HEAD")[1].split("## EXCLUDED")[0]
                self.assertIn("aion_core/tasks.py", delta)
                self.assertNotIn("aion_core/memory.py", delta)
        self.assertEqual(context.db.get_meta("last_high_model_reviewed_commit"), "HEAD")
        with self.assertRaises(ValueError):
            context.build(self.task, module="kernel.tasks", since="not-a-real-revision")

    def test_committed_delta_includes_deleted_owned_files(self):
        repo = self.tmp / "repo"
        repo.mkdir()
        def git(*args):
            return context._git(repo, *args).strip()
        git("init", "-q")
        git("config", "user.name", "Context Test")
        git("config", "user.email", "context@example.invalid")
        (repo / "aion_core").mkdir()
        source = repo / "aion_core/tasks.py"
        source.write_text("before\n")
        (repo / "unrelated.py").write_text("before\n")
        git("add", ".")
        git("commit", "-qm", "before")
        before = git("rev-parse", "HEAD")
        git("update-ref", "refs/remotes/origin/main", before)
        source.unlink()
        (repo / "unrelated.py").write_text("after\n")
        git("add", "-A")
        git("commit", "-qm", "after")
        manifest = context.util.read_json(Path(context.__file__).resolve().parents[1] /
                                         ".lucy/architecture/modules/kernel.tasks.json")
        with patch.object(context, "__file__", str(repo / "aion_core/context.py")), \
                patch.object(context.util, "read_json", return_value=manifest):
            packet = context.build(self.task, module="kernel.tasks", since=before)
        delta = packet.split("## DELTA SINCE " + before)[1].split("## EXCLUDED")[0]
        self.assertIn("aion_core/tasks.py", delta)
        self.assertNotIn("unrelated.py", delta)

    def test_json_cli_and_redaction(self):
        from aion_core import cli
        secret = "sk-" + "X" * 40
        task = tasks.create("redact " + secret)
        output = io.StringIO()
        with redirect_stdout(output):
            code = cli.main(["context", task, "--module", "kernel.tasks",
                             "--budget-bytes", "1", "--since", "HEAD", "--json"])
        self.assertEqual(code, 0)
        packet = json.loads(output.getvalue())["context"]
        self.assertIn("## MODULE kernel.tasks", packet)
        self.assertNotIn(secret, packet)
        self.assertNotIn(secret, context.build(secret))
        with patch.object(context, "_repo_sections", return_value=[secret]):
            self.assertNotIn(secret, context.build(task, module="kernel.tasks", json_output=True))
        error = io.StringIO()
        with redirect_stderr(error):
            self.assertEqual(cli.main(["context", task, "--module", "../" + secret]), 2)
        self.assertNotIn(secret, error.getvalue())

    def test_invalid_options(self):
        for kwargs in ({"module": "../tasks"}, {"module": "unknown"},
                       {"budget_bytes": -1}, {"budget_bytes": 1}, {"since": "HEAD"}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                context.build(self.task, **kwargs)


if __name__ == "__main__":
    import unittest
    unittest.main()
