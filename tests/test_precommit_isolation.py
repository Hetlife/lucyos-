"""Run an actual commit hook while its test runner creates a second repository."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class PrecommitIsolationTest(unittest.TestCase):
    def check_hook(self, runner_exit=0):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, child, bins = root / "parent", root / "child", root / "bin"
            repo.mkdir()
            bins.mkdir()
            env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
            env.update(PATH=str(bins) + os.pathsep + env["PATH"],
                       HOOK_CHILD=str(child), HOOK_TEST_EXIT=str(runner_exit))
            def git(*args, check=True):
                return subprocess.run(["git", "-C", str(repo), *args], env=env,
                                      capture_output=True, text=True, check=check, timeout=20)
            git("init", "-q")
            git("config", "user.name", "Hook test")
            git("config", "user.email", "hook-test@example.invalid")
            (repo / "tracked.txt").write_text("parent")
            git("add", "tracked.txt")
            aion = repo / "aion"
            aion.write_text("#!/bin/sh\nexit 0\n")
            aion.chmod(0o700)
            runner = bins / "python3"
            runner.write_text("""#!/bin/sh
mkdir -p "$HOOK_CHILD"
git -C "$HOOK_CHILD" init -q || exit 81
printf child > "$HOOK_CHILD/child.txt"
git -C "$HOOK_CHILD" add child.txt || exit 82
exit "$HOOK_TEST_EXIT"
""")
            runner.chmod(0o700)
            hook = repo / ".git/hooks/pre-commit"
            shutil.copyfile(Path(__file__).resolve().parents[1] / "scripts/pre-commit", hook)
            hook.chmod(0o700)
            before = git("write-tree").stdout.strip()
            env["GIT_INDEX_FILE"] = str(repo / ".git/index")
            result = git("commit", "-m", "exercise hook", check=False)
            after = git("write-tree").stdout.strip()
            self.assertEqual(before, after, result.stderr)
            self.assertEqual(git("ls-files").stdout.splitlines(), ["tracked.txt"])
            self.assertEqual(result.returncode == 0, runner_exit == 0, result.stderr)

    def test_nested_git_does_not_mutate_parent_index(self):
        self.check_hook()

    def test_failing_suite_still_blocks_commit_without_mutating_index(self):
        self.check_hook(runner_exit=3)
