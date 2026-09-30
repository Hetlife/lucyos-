import os
import re
import subprocess
import unittest


SCRIPT = os.path.join(
    os.path.dirname(__file__),
    "..",
    "platforms",
    "nebula",
    "native",
    "S99zz_lucynest",
)


def read_script():
    with open(SCRIPT, "r", encoding="utf-8") as fh:
        return fh.read()


def writes_into_initd(line):
    if "/etc/init.d" not in line:
        return False
    return any(tok in line for tok in (">", "cp ", "mv ", "install "))


class BootScriptTest(unittest.TestCase):
    def setUp(self):
        self.text = read_script()
        self.lines = self.text.splitlines()

    def test_script_parses(self):
        proc = subprocess.run(["sh", "-n", SCRIPT], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_no_writes_into_etc_init_d(self):
        bad = [line for line in self.lines if writes_into_initd(line)]
        self.assertEqual(bad, [], "writes into /etc/init.d detected: %r" % bad)

    def test_backup_dir_assignment(self):
        m = re.search(r"^BACKUP_DIR=(.+)$", self.text, re.M)
        self.assertIsNotNone(m, "BACKUP_DIR assignment missing")
        value = m.group(1).strip().strip('"\'')
        self.assertFalse(value.startswith("/etc/init.d"), value)

    def test_backup_helper_referenced(self):
        self.assertIn("backup_copy", self.text)

    def test_original_safety_behavior_intact(self):
        self.assertIn("client.py", self.text)
        self.assertIn("client.pid", self.text)
        self.assertIn("/dev/fb1", self.text)

    def test_negative_control_flags_initd_write_line(self):
        self.assertTrue(writes_into_initd("cp x /etc/init.d/foo.bak"))


if __name__ == "__main__":
    unittest.main()
