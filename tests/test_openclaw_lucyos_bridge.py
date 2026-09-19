import os
import subprocess
import shutil
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "integrations" / "openclaw" / "lucyos" / "scripts"
DISPATCH = SCRIPTS / "lucyos-remote-dispatch"
CTL = SCRIPTS / "lucyosctl"
ENROLL = SCRIPTS / "enroll-client-public-key"


class OpenClawLucyBridgeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.tmp_path = Path(self.tmp.name)
        self.fake_aion = self.tmp_path / "aion"
        self.fake_aion.write_text(textwrap.dedent("""\
            #!/usr/bin/env python3
            import pathlib, sys
            print("ARGS=" + "|".join(sys.argv[1:]))
            if len(sys.argv) >= 3 and sys.argv[1] == "architecture-check":
                print("BODY=" + pathlib.Path(sys.argv[2]).read_text())
        """))
        self.fake_aion.chmod(0o755)

    def dispatch(self, command, stdin=b""):
        env = os.environ.copy()
        env["SSH_ORIGINAL_COMMAND"] = command
        env["LUCYOS_AION_BIN"] = str(self.fake_aion)
        env["AION_HOME"] = str(self.tmp_path / "brain")
        return subprocess.run(
            [str(DISPATCH)], input=stdin, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
    def test_dispatch_defaults_to_repo_relative_aion(self):
        env = os.environ.copy()
        env.pop("LUCYOS_AION_BIN", None)
        env["SSH_ORIGINAL_COMMAND"] = "status"
        env["AION_HOME"] = str(self.tmp_path / "brain")
        result = subprocess.run(
            [str(DISPATCH)], env=env, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertNotIn("/root/lucyos/aion", DISPATCH.read_text())

    def test_simple_command_maps_without_shell(self):
        result = self.dispatch("status")
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertIn("ARGS=status", result.stdout.decode())

    def test_shell_injection_is_refused(self):
        for command in ("status; id", "status && id", "$(id)", "status extra"):
            result = self.dispatch(command)
            self.assertNotEqual(result.returncode, 0, command)
            self.assertIn("bridge refused", result.stderr.decode())

    def test_context_requires_bounded_task_id(self):
        good = self.dispatch("context TASK-ABC123")
        self.assertEqual(good.returncode, 0, good.stderr.decode())
        self.assertIn("ARGS=context|TASK-ABC123", good.stdout.decode())
        bad = self.dispatch("context ../../etc/passwd")
        self.assertNotEqual(bad.returncode, 0)

    def test_work_dry_is_bounded(self):
        good = self.dispatch("work-dry 3")
        self.assertEqual(good.returncode, 0)
        self.assertIn("ARGS=work|--max|3|--dry-run", good.stdout.decode())
        self.assertNotEqual(self.dispatch("work-dry 11").returncode, 0)

    def test_architecture_check_accepts_only_stdin_json(self):
        body = b'{"skill_id":"core.node-federation"}'
        result = self.dispatch("architecture-check", body)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        text = result.stdout.decode()
        self.assertIn("ARGS=architecture-check|", text)
        self.assertIn('BODY={"skill_id":"core.node-federation"}', text)
    def make_fake_ssh(self):
        bindir = self.tmp_path / "bin"
        bindir.mkdir(exist_ok=True)
        ssh = bindir / "ssh"
        ssh.write_text(textwrap.dedent("""\
            #!/usr/bin/env python3
            import sys
            print("SSH=" + "|".join(sys.argv[1:]))
            if sys.argv[-1:] == ["architecture-check"]:
                data = sys.stdin.read()
                if data:
                    print("STDIN=" + data)
        """))
        ssh.chmod(0o755)
        return bindir

    def run_ctl_remote(self, *args, stdin_file=None):
        bindir = self.make_fake_ssh()
        env = os.environ.copy()
        env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
        env["LUCYOS_REMOTE_SSH_TARGET"] = "lucyos-bridge@mark2"
        env["LUCYOS_REMOTE_SSH_PORT"] = "22"
        return subprocess.run(
            [str(CTL), *args], env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )

    def test_remote_client_uses_batch_ssh_and_bounded_command(self):
        result = self.run_ctl_remote("status")
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        text = result.stdout.decode()
        self.assertIn("BatchMode=yes", text)
        self.assertIn("ClearAllForwardings=yes", text)
        self.assertIn("lucyos-bridge@mark2|status", text)

    def test_remote_client_rejects_bad_context_before_ssh(self):
        result = self.run_ctl_remote("context", "../../etc/passwd")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("SSH=", result.stdout.decode())


if __name__ == "__main__":
    unittest.main()
# Remote architecture-check stdin transport is covered indirectly by the
# dispatcher stdin test plus the fake-ssh client harness above. The client
# rejects non-files before SSH, so only explicit local proposal files can be sent.

class PublicKeyEnrollmentTest(unittest.TestCase):
    @unittest.skipUnless(shutil.which("ssh-keygen"), "ssh-keygen not available")
    def test_enrollment_is_restricted_and_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            key = root / "client"
            auth = root / "authorized_keys"
            subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True)
            auth.write_text("")
            env = os.environ.copy()
            env["LUCYOS_AUTHORIZED_KEYS"] = str(auth)
            env["LUCYOS_REMOTE_DISPATCH"] = str(DISPATCH)
            pub = key.with_suffix(".pub").read_text()
            for _ in range(2):
                subprocess.run([str(ENROLL), "scs-test"], input=pub, text=True, env=env, check=True, capture_output=True)
            lines = auth.read_text().splitlines()
            self.assertEqual(len(lines), 1)
            self.assertIn('restrict,command="', lines[0])
            self.assertIn("lucyos-scs-test", lines[0])
