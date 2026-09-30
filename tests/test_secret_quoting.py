"""The secret store is written by Python but loaded by a shell `source` in the
bridge service. These tests prove both read back the exact bytes for hostile
values, that files written before quoting still work, and that every reader of
the store goes through the one shared parser."""
import importlib.util
import io
import subprocess
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from aion_core import backup, bootstrap, cli, config, db, model_gateway, sevaa
from tests.base import AionTest

ROOT = Path(__file__).resolve().parents[1]
NAME = "SECRET_UNDER_TEST"

HOSTILE = [
    "plain",
    "my secret",
    "a&b",
    "pa$word",
    "abc#def",
    "x;echo INJECTED",
    "back`tick`",
    'dq"quote',
    "sq'quote",
    "'",
    "''",
    "back\\slash",
    "trailing backslash\\",
    "$(echo hi)",
    "`id`",
    "*glob*",
    "=equals=",
    "  leading and trailing  ",
    "ünïcödé ✓",
    "tab\tinside",
]


def _shell_loads(secrets_file: Path, name: str) -> str:
    """Load the file exactly the way the service unit does."""
    done = subprocess.run(
        ["bash", "-c", 'set -a; . "$1"; set +a; printf %s "${!2}"', "_", str(secrets_file), name],
        capture_output=True, text=True, timeout=10)
    assert done.stderr == "", "shell complained: %r" % done.stderr[:80]
    return done.stdout


def _load_http_server():
    spec = importlib.util.spec_from_file_location("http_server_for_quoting",
                                                  ROOT / "bridges" / "http_server.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestRoundTrip(AionTest):
    def test_python_and_a_real_shell_both_read_back_the_exact_value(self):
        for value in HOSTILE:
            with self.subTest(value=value):
                bootstrap.set_secret(NAME, value)
                self.assertEqual(bootstrap.read_secret(NAME), value)
                self.assertEqual(_shell_loads(config.secrets_file(), NAME), value)
                self.assertTrue(bootstrap.has_secret(NAME))

    def test_an_injection_attempt_is_stored_as_data_not_run(self):
        bootstrap.set_secret(NAME, "x;echo INJECTED")
        done = subprocess.run(
            ["bash", "-c", 'set -a; . "$1"; set +a', "_", str(config.secrets_file())],
            capture_output=True, text=True, timeout=10)
        self.assertEqual(done.stdout, "")  # nothing executed
        self.assertEqual(done.stderr, "")

    def test_overwriting_leaves_exactly_one_line_with_the_latest_value(self):
        bootstrap.set_secret(NAME, "first")
        bootstrap.set_secret(NAME, "second value")
        lines = [l for l in config.secrets_file().read_text().splitlines()
                 if l.startswith(NAME + "=")]
        self.assertEqual(len(lines), 1)
        self.assertEqual(bootstrap.read_secret(NAME), "second value")

    def test_file_mode_stays_0600(self):
        bootstrap.set_secret(NAME, "v")
        self.assertEqual(config.secrets_file().stat().st_mode & 0o777, 0o600)

    def test_empty_value_is_stored_but_counts_as_not_set(self):
        bootstrap.set_secret(NAME, "")
        self.assertFalse(bootstrap.has_secret(NAME))
        self.assertIsNone(bootstrap.read_secret(NAME))

    def test_value_is_not_recorded_in_the_events_log(self):
        bootstrap.set_secret(NAME, "uniqvalue-9Q")
        rows = db.connect().execute("SELECT subject, detail FROM events").fetchall()
        self.assertNotIn("uniqvalue-9Q", " ".join(f"{r['subject']} {r['detail']}" for r in rows))


class TestRefusals(AionTest):
    def test_line_breaks_and_nul_are_refused_not_guessed(self):
        for bad in ("a\nb", "a\rb", "a\x00b", "a b", "a\x0cb", "a\x85b"):
            with self.subTest(bad=repr(bad)):
                with self.assertRaises(ValueError):
                    bootstrap.set_secret(NAME, bad)
        self.assertFalse(config.secrets_file().exists()
                         and NAME in config.secrets_file().read_text())

    def test_invalid_names_are_refused(self):
        for bad in ("", "1ABC", "A-B", "A B", "A=B", "A;B"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    bootstrap.set_secret(bad, "v")


class TestLegacyFilesStillWork(AionTest):
    """Files written before quoting hold raw NAME=value lines."""

    def _legacy(self, *lines):
        bootstrap.init_secret_store()
        config.secrets_file().write_text("\n".join(lines) + "\n")

    def test_shared_parser_reads_legacy_unquoted_values(self):
        self._legacy("# comment", "PLAIN_ONE=abc123", "SPACED=two words", "EMPTY=")
        self.assertEqual(bootstrap.read_secret("PLAIN_ONE"), "abc123")
        self.assertEqual(bootstrap.read_secret("SPACED"), "two words")
        self.assertIsNone(bootstrap.read_secret("EMPTY"))
        self.assertIsNone(bootstrap.read_secret("ABSENT"))

    def test_every_reader_reads_a_legacy_file(self):
        http_server = _load_http_server()
        iface = "AION_INTERFACE_TOKEN"
        self._legacy(f"{iface}=legacy-token", "OPENROUTER_API_" + "KEY=legacy-key",  # split: keeps a credential-shaped literal out of the repo
                     f"{sevaa.AUTOMATION_TOKEN_NAME}=legacy-sevaa",
                     f"{backup.PASSPHRASE_SECRET_NAME}=legacy pass phrase")
        self.assertEqual(http_server.read_secret("AION_INTERFACE_TOKEN"), "legacy-token")
        self.assertEqual(model_gateway._secret("OPENROUTER_API_KEY"), "legacy-key")
        self.assertEqual(sevaa._read_secret(sevaa.AUTOMATION_TOKEN_NAME), "legacy-sevaa")
        self.assertEqual(backup._read_secret(backup.PASSPHRASE_SECRET_NAME),
                         "legacy pass phrase")

    def test_a_new_write_next_to_legacy_lines_leaves_them_intact(self):
        self._legacy("OLD_ONE=oldvalue")
        bootstrap.set_secret("NEW_ONE", "new value")
        self.assertEqual(bootstrap.read_secret("OLD_ONE"), "oldvalue")
        self.assertEqual(bootstrap.read_secret("NEW_ONE"), "new value")


class TestEveryReaderUsesTheSharedParser(AionTest):
    def test_all_readers_return_a_quoted_hostile_value_exactly(self):
        http_server = _load_http_server()
        hostile = "pa$s w'or\"d;&#"
        for name, reader in (
                ("AION_INTERFACE_TOKEN", http_server.read_secret),
                ("OPENROUTER_API_KEY", model_gateway._secret),
                (sevaa.AUTOMATION_TOKEN_NAME, sevaa._read_secret),
                (backup.PASSPHRASE_SECRET_NAME, backup._read_secret)):
            with self.subTest(reader=name):
                bootstrap.set_secret(name, hostile)
                self.assertEqual(reader(name), hostile)

    def test_no_reader_keeps_its_own_copy_of_the_parsing_loop(self):
        for rel in ("aion_core/backup.py", "aion_core/sevaa.py",
                    "aion_core/model_gateway.py", "bridges/http_server.py"):
            with self.subTest(file=rel):
                src = (ROOT / rel).read_text()
                self.assertIn("bootstrap.read_secret", src)
                self.assertNotIn('line.split("=", 1)', src)
                self.assertNotIn("prefix = f\"{name}=\"", src)

    def test_secrets_list_shows_names_only(self):
        bootstrap.set_secret(NAME, "uniqvalue-7Z")
        buf = io.StringIO()
        with redirect_stdout(buf):
            cli.main(["secrets", "list"])
        self.assertIn(NAME, buf.getvalue())
        self.assertNotIn("uniqvalue-7Z", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
