"""TR-1-03: the governed `whatsapp` verb on the OpenClaw bridge.

Covers the three layers of one door: the CLI (authoritative validation, event,
router), the forced-command dispatcher (shape, identity, bounds) and lucyosctl
(local and remote client). No secret values are written here; fixtures that need
one are assembled at run time.
"""
import base64
import contextlib
import hashlib
import io
import os
import shlex
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

from aion_core import approvals, cli, db, router
from tests.base import AionTest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "integrations" / "openclaw" / "lucyos" / "scripts"
DISPATCH = SCRIPTS / "lucyos-remote-dispatch"
CTL = SCRIPTS / "lucyosctl"
PRINCIPAL = "+911234567890"

FAKE_AION = textwrap.dedent("""\
    #!/usr/bin/env python3
    import sys
    print("ARGS=" + "|".join(sys.argv[1:]))
""")
FAKE_SSH = textwrap.dedent("""\
    #!/usr/bin/env python3
    import sys
    print("SSH=" + "|".join(sys.argv[1:]))
""")


def bridge(*words, principal=PRINCIPAL, key_id=None):
    argv = ["whatsapp", "--channel", "openclaw", "--principal", principal]
    if key_id:
        argv += ["--key-id", key_id]
    return argv + ["--", *words]


def run_cli(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = cli.main(argv)
    return rc, out.getvalue(), err.getvalue()


def bridge_events():
    rows = db.connect().execute(
        "SELECT actor, kind, subject, detail FROM events WHERE kind='openclaw'").fetchall()
    return [tuple(r) for r in rows]


def new_approval():
    return approvals.create("TR-1-03 probe", why="test", cost="none", reversibility="full",
                            prepared="nothing", resumes="nothing")


class BridgeCliTest(AionTest):
    def test_bridge_reply_matches_plain_cli_and_plain_path_is_unchanged(self):
        rc_plain, plain, _ = run_cli(["whatsapp", "help"])
        rc_bridge, via, _ = run_cli(bridge("help"))
        self.assertEqual((rc_plain, rc_bridge), (0, 0))
        self.assertEqual(plain, via)
        self.assertEqual(bridge_events(), [bridge_events()[0]])  # exactly one bridge event
        # The plain path writes no bridge event.
        run_cli(["whatsapp", "help"])
        self.assertEqual(len(bridge_events()), 1)

    def test_approve_transitions_the_approval_and_attributes_the_decision(self):
        aid = new_approval()
        rc, out, _ = run_cli(bridge("approve", aid))
        self.assertEqual(rc, 0, out)
        row = approvals.get(aid)
        self.assertEqual(row["status"], "APPROVED")
        self.assertEqual(row["decided_by"], "openclaw:" + PRINCIPAL)

    def test_deny_goes_through_the_same_door(self):
        aid = new_approval()
        rc, _, _ = run_cli(bridge("deny " + aid))
        self.assertEqual(rc, 0)
        self.assertEqual(approvals.get(aid)["status"], "DENIED")

    def test_pause_and_resume_change_state(self):
        run_cli(bridge("pause"))
        self.assertTrue(router.is_paused())
        run_cli(bridge("resume"))
        self.assertFalse(router.is_paused())

    def test_event_carries_principal_and_verb_but_never_the_body(self):
        marker = "ZEBRA-MARKER-7731"
        rc, _, _ = run_cli(bridge("why", marker))
        self.assertEqual(rc, 0)
        events = bridge_events()
        self.assertEqual(len(events), 1)
        actor, kind, subject, detail = events[0]
        self.assertEqual((actor, kind, subject), ("whatsapp", "openclaw", PRINCIPAL))
        self.assertEqual(detail, "verb=why key_id=-")
        self.assertNotIn(marker, " ".join(events[0]))

    def test_key_id_is_recorded_and_may_hold_fingerprint_characters(self):
        key_id = "SHA256:ab+cd/ef=="
        run_cli(bridge("help", key_id=key_id))
        self.assertEqual(bridge_events()[0][3], "verb=help key_id=" + key_id)

    def test_a_credential_is_refused_and_never_reaches_the_event_log(self):
        secret = "gh" + "p_" + "AbCdEfGhIjKlMnOpQrStUvWxYz012345"  # assembled at run time
        rc, out, _ = run_cli(bridge("use " + secret))
        self.assertEqual(rc, 0)
        self.assertIn(router.SECRET_REFUSAL.splitlines()[0], out)
        everything = db.connect().execute("SELECT actor||kind||subject||detail FROM events").fetchall()
        self.assertNotIn(secret, " ".join(r[0] for r in everything))
        self.assertEqual(bridge_events()[0][3], "verb=use key_id=-")
        # A credential as the FIRST word can never be logged as the verb.
        run_cli(bridge(secret))
        self.assertEqual(bridge_events()[1][3], "verb=other key_id=-")

    def assert_refused(self, argv, fragment=""):
        before = db.connect().execute("SELECT COUNT(*) FROM events").fetchone()[0]
        tasks_before = db.connect().execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        rc, out, err = run_cli(argv)
        self.assertEqual(rc, 2, (argv, out, err))
        self.assertIn(fragment, err)
        self.assertEqual(out, "")
        self.assertEqual(db.connect().execute("SELECT COUNT(*) FROM events").fetchone()[0], before)
        self.assertEqual(db.connect().execute("SELECT COUNT(*) FROM tasks").fetchone()[0], tasks_before)

    def test_control_characters_and_newlines_are_refused_before_anything_is_stored(self):
        for text in ("status\nstatus", "status\r", "sta\ttus", "bell\x07", "esc\x1b[31m", "nul\x00"):
            self.assert_refused(bridge(text), "control character")

    def test_message_size_is_bounded_in_bytes_not_characters(self):
        rc, _, _ = run_cli(bridge("a" * 512))
        self.assertEqual(rc, 0)
        rc, _, _ = run_cli(bridge("é" * 256))  # 512 bytes
        self.assertEqual(rc, 0)
        self.assert_refused(bridge("a" * 513), "exceeds 512 bytes")
        self.assert_refused(bridge("é" * 257), "exceeds 512 bytes")  # 257 chars, 514 bytes

    def test_empty_message_is_refused(self):
        self.assert_refused(bridge("   "), "empty")

    def test_unattributed_or_malformed_identity_is_refused(self):
        self.assert_refused(["whatsapp", "--channel", "openclaw", "--", "help"], "required together")
        self.assert_refused(["whatsapp", "--principal", PRINCIPAL, "--", "help"], "required together")
        self.assert_refused(["whatsapp", "--key-id", "k", "--", "help"], "required together")
        for bad in ("a b", "x;id", "$(id)", "a" * 65, "é", "a\nb"):
            self.assert_refused(bridge("help", principal=bad), "invalid --principal")
        for bad in ("a b", "x;id", "a" * 129):
            self.assert_refused(bridge("help", key_id=bad), "invalid --key-id")


class DispatcherWhatsappTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.fake = self.dir / "aion"
        self.fake.write_text(FAKE_AION)
        self.fake.chmod(0o755)

    def dispatch(self, command, *argv, env_extra=None):
        env = os.environ.copy()
        env.pop("SSH_USER_AUTH", None)
        env["SSH_ORIGINAL_COMMAND"] = command
        env["LUCYOS_AION_BIN"] = str(self.fake)
        env["AION_HOME"] = str(self.dir / "brain")
        env.update(env_extra or {})
        return subprocess.run([str(DISPATCH), *argv], env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, check=False)

    def test_single_quoted_message_maps_to_the_bridge_argv(self):
        r = self.dispatch("whatsapp 'approve A-1'", "--key-id", "scs-admin")
        self.assertEqual(r.returncode, 0, r.stderr.decode())
        self.assertIn("ARGS=whatsapp|--channel|openclaw|--principal|key:scsadmin|"
                      "--key-id|scs-admin|--|approve A-1", r.stdout.decode())

    def test_wrong_shapes_are_refused(self):
        for command in ("whatsapp", "whatsapp approve A-1", "whatsapp 'a' 'b'", "whatsapp ''",
                        "whatsapp '   '", "whatsapp 'status'; id", "whatsapp status && id"):
            r = self.dispatch(command, "--key-id", "k")
            self.assertNotEqual(r.returncode, 0, command)
            self.assertIn("bridge refused", r.stderr.decode(), command)
            self.assertNotIn("ARGS=", r.stdout.decode(), command)

    def test_shell_syntax_inside_the_quoted_message_is_data_never_executed(self):
        marker = self.dir / "pwned"
        text = "$(touch %s) `touch %s` ; touch %s" % ((marker,) * 3)
        r = self.dispatch("whatsapp " + shlex.quote(text), "--key-id", "k")
        self.assertEqual(r.returncode, 0, r.stderr.decode())
        self.assertIn("|--|" + text, r.stdout.decode())  # passed to aion verbatim, as one argument
        self.assertFalse(marker.exists())

    def test_control_characters_newlines_and_oversize_are_refused(self):
        for text in ("a\nb", "a\rb", "a\tb", "a\x07b", "a" * 513, "é" * 257):
            r = self.dispatch("whatsapp " + shlex.quote(text), "--key-id", "k")
            self.assertEqual(r.returncode, 2, repr(text[:20]))
            self.assertNotIn("ARGS=", r.stdout.decode())

    def test_message_at_the_limit_passes_even_when_every_character_needs_quoting(self):
        for text in ("a" * 512, "é" * 256, "'" * 512):
            r = self.dispatch("whatsapp " + shlex.quote(text), "--key-id", "k")
            self.assertEqual(r.returncode, 0, (repr(text[:8]), r.stderr.decode()))
            self.assertIn("|--|" + text, r.stdout.decode())

    def test_other_commands_keep_the_512_byte_cap(self):
        r = self.dispatch("status " + "a" * 600)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("command too long", r.stderr.decode())

    def test_no_enrolled_key_identity_fails_closed(self):
        r = self.dispatch("whatsapp 'approve A-1'")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("enrolled key identity", r.stderr.decode())
        self.assertNotIn("ARGS=", r.stdout.decode())

    def test_client_supplied_identity_paths_are_not_honoured(self):
        r = self.dispatch("whatsapp 'approve A-1'",
                          env_extra={"LUCYOS_PRINCIPAL": PRINCIPAL, "LUCYOS_KEY_ID": "spoofed"})
        self.assertNotEqual(r.returncode, 0)

    def test_identity_comes_from_the_key_sshd_authenticated(self):
        blob = b"\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20" + bytes(range(32))
        auth = self.dir / "auth-info"
        auth.write_text("publickey ssh-ed25519 " + base64.b64encode(blob).decode() + "\n")
        expected = "SHA256:" + base64.b64encode(hashlib.sha256(blob).digest()).decode().rstrip("=")
        r = self.dispatch("whatsapp 'status'", "--key-id", "label-loses",
                          env_extra={"SSH_USER_AUTH": str(auth)})
        self.assertEqual(r.returncode, 0, r.stderr.decode())
        self.assertIn("--key-id|" + expected + "|--|status", r.stdout.decode())

    def test_unreadable_or_garbage_auth_info_is_not_an_identity(self):
        garbage = self.dir / "auth-info"
        garbage.write_text("publickey ssh-ed25519 !!!not-base64!!!\n")
        for value in (str(garbage), str(self.dir / "missing")):
            r = self.dispatch("whatsapp 'status'", env_extra={"SSH_USER_AUTH": value})
            self.assertNotEqual(r.returncode, 0)

    def test_forced_command_arguments_are_strict(self):
        for argv in (("--bogus",), ("--key-id",), ("--key-id", "a b"), ("--key-id", "x", "y")):
            r = self.dispatch("whatsapp 'status'", *argv)
            self.assertNotEqual(r.returncode, 0, argv)
            self.assertNotIn("ARGS=", r.stdout.decode(), argv)


class CtlWhatsappTest(AionTest):
    def setUp(self):
        super().setUp()
        self.fake = self.tmp / "fake-aion"
        self.fake.write_text(FAKE_AION)
        self.fake.chmod(0o755)
        bindir = self.tmp / "bin"
        bindir.mkdir()
        ssh = bindir / "ssh"
        ssh.write_text(FAKE_SSH)
        ssh.chmod(0o755)
        self.bindir = bindir

    def ctl(self, *args, env_extra=None, fake_aion=True, remote=False):
        env = os.environ.copy()
        for key in ("LUCYOS_PRINCIPAL", "LUCYOS_KEY_ID", "LUCYOS_REMOTE_SSH_TARGET"):
            env.pop(key, None)
        if fake_aion:
            env["LUCYOS_AION_BIN"] = str(self.fake)
        if remote:
            env["PATH"] = str(self.bindir) + os.pathsep + env.get("PATH", "")
            env["LUCYOS_REMOTE_SSH_TARGET"] = "lucyos-bridge@mark2"
        env.update(env_extra or {})
        return subprocess.run([str(CTL), *args], env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, check=False)

    def test_local_mode_passes_principal_channel_and_message(self):
        r = self.ctl("whatsapp", "approve A-1", env_extra={"LUCYOS_PRINCIPAL": PRINCIPAL})
        self.assertEqual(r.returncode, 0, r.stderr.decode())
        self.assertIn("ARGS=whatsapp|--channel|openclaw|--principal|" + PRINCIPAL + "|--|approve A-1",
                      r.stdout.decode())

    def test_local_mode_forwards_an_optional_key_id(self):
        r = self.ctl("whatsapp", "status",
                     env_extra={"LUCYOS_PRINCIPAL": PRINCIPAL, "LUCYOS_KEY_ID": "gateway-1"})
        self.assertIn("|--key-id|gateway-1|--|status", r.stdout.decode())

    def test_local_mode_refuses_without_a_principal_or_with_bad_arity(self):
        cases = (
            (("whatsapp", "status"), {}),
            (("whatsapp", "status"), {"LUCYOS_PRINCIPAL": ""}),
            (("whatsapp",), {"LUCYOS_PRINCIPAL": PRINCIPAL}),
            (("whatsapp", "approve", "A-1"), {"LUCYOS_PRINCIPAL": PRINCIPAL}),
            (("whatsapp", ""), {"LUCYOS_PRINCIPAL": PRINCIPAL}),
        )
        for args, env in cases:
            r = self.ctl(*args, env_extra=env)
            self.assertEqual(r.returncode, 2, args)
            self.assertNotIn("ARGS=", r.stdout.decode(), args)

    def test_real_aion_end_to_end_matches_aion_whatsapp(self):
        aid = new_approval()
        r = self.ctl("whatsapp", "approve " + aid, fake_aion=False,
                     env_extra={"LUCYOS_PRINCIPAL": PRINCIPAL})
        self.assertEqual(r.returncode, 0, r.stderr.decode())
        row = approvals.get(aid)
        self.assertEqual((row["status"], row["decided_by"]), ("APPROVED", "openclaw:" + PRINCIPAL))
        via_ctl = self.ctl("whatsapp", "help", fake_aion=False, env_extra={"LUCYOS_PRINCIPAL": PRINCIPAL})
        plain = subprocess.run([str(ROOT / "aion"), "whatsapp", "help"], env=os.environ.copy(),
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        self.assertEqual(via_ctl.stdout, plain.stdout)

    def test_real_aion_refuses_oversize_and_control_characters_with_exit_2(self):
        env = {"LUCYOS_PRINCIPAL": PRINCIPAL}
        for text in ("a" * 513, "two\nlines", "bell\x07"):
            r = self.ctl("whatsapp", text, fake_aion=False, env_extra=env)
            self.assertEqual(r.returncode, 2, repr(text[:12]))
            self.assertEqual(r.stdout, b"")

    def test_remote_mode_sends_one_quoted_argument_that_the_dispatcher_splits_back(self):
        for text in ("approve A-1", "it's ok", 'say "hi" $HOME `id`; rm -rf', "héllo 👍", "a\\b"):
            r = self.ctl("whatsapp", text, remote=True)
            self.assertEqual(r.returncode, 0, r.stderr.decode())
            line = r.stdout.decode().strip()
            self.assertIn("BatchMode=yes", line)
            sent = line.split("|whatsapp|", 1)[1]
            # ssh appends the remote command to the target; sshd hands the joined string to
            # the forced command, which splits it exactly as the dispatcher does.
            self.assertEqual(shlex.split("whatsapp " + sent), ["whatsapp", text])

    def test_remote_mode_does_not_transmit_a_client_asserted_principal(self):
        r = self.ctl("whatsapp", "status", remote=True, env_extra={"LUCYOS_PRINCIPAL": PRINCIPAL})
        self.assertNotIn(PRINCIPAL, r.stdout.decode())

    def test_remote_mode_refuses_bad_input_before_ssh(self):
        for args in (("whatsapp",), ("whatsapp", "a", "b"), ("whatsapp", ""), ("whatsapp", "a\nb")):
            r = self.ctl(*args, remote=True)
            self.assertEqual(r.returncode, 2, args)
            self.assertNotIn("SSH=", r.stdout.decode(), args)


if __name__ == "__main__":
    unittest.main()
