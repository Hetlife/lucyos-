import importlib
import json
import os
import py_compile
import queue
import re
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import unittest.mock
from contextlib import ExitStack
from pathlib import Path

from devices.little_lucy.platforms.nebula.native import client, lucynest_ctl
from devices.little_lucy.platforms.nebula.native.ui import render

NATIVE = Path(client.__file__).resolve().parent


def wait_for(path, timeout=5.0):
    """Wait until the path is a socket that actually accepts connections."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if stat.S_ISSOCK(os.lstat(path).st_mode):
                probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                probe.settimeout(0.2)
                try:
                    probe.connect(path)
                    probe.close()
                    return True
                except OSError:
                    pass
                finally:
                    try: probe.close()
                    except OSError: pass
        except OSError:
            pass
        time.sleep(0.02)
    return False


class ControlRequestParsingTests(unittest.TestCase):
    def test_parses_verb_and_optional_arg(self):
        self.assertEqual(client.parse_control_request("status"), ("status", None))
        self.assertEqual(client.parse_control_request("inbox"), ("inbox", None))
        self.assertEqual(client.parse_control_request(b"next\n"), ("next", None))
        self.assertEqual(client.parse_control_request("send A-1"), ("send", "A-1"))

    def test_rejects_oversize_non_utf8_empty_and_multiline(self):
        with self.assertRaises(ValueError):
            client.parse_control_request(b"x" * 257)
        with self.assertRaises(ValueError):
            client.parse_control_request(b"\xff\xfe")
        with self.assertRaises(ValueError):
            client.parse_control_request(b"")
        with self.assertRaises(ValueError):
            client.parse_control_request("status\nhome")
        with self.assertRaises(ValueError):
            client.parse_control_request(" status")

    def test_nav_verbs_exclude_decision_verbs(self):
        self.assertTrue(client.NAV_VERBS)
        self.assertTrue(client.NAV_VERBS.isdisjoint(client.DECISION_VERBS))
        self.assertNotIn("send", client.NAV_VERBS)
        self.assertEqual(client.DECISION_VERBS, frozenset(("approve", "deny", "send")))


class ControlServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.sock_path = os.path.join(self.tmp.name, "control.sock")
        self.events = queue.Queue()
        self.stop = threading.Event()
        self.threads = []

    def tearDown(self):
        self.stop.set()
        for thread in self.threads:
            thread.join(timeout=5)
        self.tmp.cleanup()

    def start(self, allowed_uid=None, sock_path=None):
        path = sock_path or self.sock_path
        thread = threading.Thread(
            target=client.control_server_thread,
            args=(self.events, self.stop),
            kwargs={"sock_path": path, "allowed_uid": os.getuid() if allowed_uid is None else allowed_uid},
            daemon=True,
        )
        thread.start()
        self.threads.append(thread)
        return path

    def exchange(self, line, path=None, uid_rejected=False):
        path = path or self.sock_path
        conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        conn.settimeout(5)
        conn.connect(path)
        try:
            conn.sendall(line.encode("utf-8"))
            buf = b""
            while b"\n" not in buf:
                chunk = conn.recv(1024)
                if not chunk:
                    break
                buf += chunk
        finally:
            conn.close()
        return json.loads(buf.split(b"\n", 1)[0].decode("utf-8"))

    def drain_control_events(self):
        found = []
        while True:
            try:
                kind, value = self.events.get_nowait()
            except queue.Empty:
                return found
            if kind == "control":
                found.append((kind, value))
                value["reply"].put({"ok": True, "page": "home"})

    def test_peer_uid_is_enforced(self):
        self.start(allowed_uid=os.getuid() + 1)
        self.assertTrue(wait_for(self.sock_path))
        reply = self.exchange("status")
        self.assertFalse(reply["ok"])
        self.assertIn("refused", reply["error"])

    def test_peer_uid_accepted_for_matching_uid(self):
        self.start()
        self.assertTrue(wait_for(self.sock_path))
        with main_loop_consumer(self.events, pending_model(), queue.Queue()):
            reply = self.exchange("status")
        self.assertTrue(reply["ok"])

    def test_socket_and_dir_permissions(self):
        self.start()
        self.assertTrue(wait_for(self.sock_path))
        dir_mode = stat.S_IMODE(os.lstat(self.tmp.name).st_mode)
        sock_mode = stat.S_IMODE(os.lstat(self.sock_path).st_mode)
        self.assertEqual(dir_mode, 0o700)
        self.assertEqual(sock_mode, 0o600)

    def test_symlinked_socket_dir_is_refused(self):
        real = tempfile.mkdtemp(dir=self.tmp.name)
        link = os.path.join(self.tmp.name, "link")
        os.symlink(real, link)
        self.start(sock_path=os.path.join(link, "control.sock"))
        kind, value = self.events.get(timeout=5)
        self.assertEqual(kind, "control_error")
        self.assertIn("not a real directory", value)
        self.assertFalse(os.path.exists(os.path.join(link, "control.sock")))

    def test_non_socket_stale_path_is_refused(self):
        with open(self.sock_path, "w") as handle:
            handle.write("not a socket")
        self.start()
        kind, value = self.events.get(timeout=5)
        self.assertEqual(kind, "control_error")
        self.assertIn("not a socket", value)
        with open(self.sock_path) as handle:
            self.assertEqual(handle.read(), "not a socket")

    def test_stale_socket_path_is_replaced(self):
        stale = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        stale.bind(self.sock_path)
        stale.close()
        self.start()
        self.assertTrue(wait_for(self.sock_path))
        with main_loop_consumer(self.events, pending_model(), queue.Queue()):
            self.assertTrue(self.exchange("status")["ok"])

    def test_shutdown_unlinks_only_a_socket(self):
        self.start()
        self.assertTrue(wait_for(self.sock_path))
        self.stop.set()
        self.threads[-1].join(timeout=5)
        self.assertFalse(os.path.exists(self.sock_path))
        # A non-socket file at the path is left alone on shutdown.
        with open(self.sock_path, "w") as handle:
            handle.write("keep me")
        thread = threading.Thread(
            target=client.control_server_thread,
            args=(self.events, self.stop),
            kwargs={"sock_path": self.sock_path},
            daemon=True,
        )
        thread.start()
        kind, _ = self.events.get(timeout=5)
        self.assertEqual(kind, "control_error")
        thread.join(timeout=5)
        self.assertTrue(os.path.exists(self.sock_path))


def pending_model():
    return {
        "page": "inbox",
        "online": True,
        "updated": 123.5,
        "touch_status": "ok",
        "data": {"approvals": [{"approval_id": "A-1", "action": "Deploy thing", "revision": "r1"}]},
        "index": 0,
    }


class MainLoopConsumer:
    """Background, main-loop-shaped consumer: drains control events via handle_control."""

    def __init__(self, events, model, commands):
        self.events = events
        self.model = model
        self.commands = commands
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.loop, daemon=True)

    def loop(self):
        while not self.stop.is_set():
            try:
                kind, ev = self.events.get(timeout=0.1)
            except queue.Empty:
                continue
            if kind == "control":
                command = client.handle_control(self.model, ev)
                if command:
                    self.commands.put(command)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.stop.set()
        self.thread.join(timeout=5)
        return False


def main_loop_consumer(events, model, commands):
    return MainLoopConsumer(events, model, commands)


class GateTestMixin(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.gate = os.path.join(self.tmp.name, "remote-decisions.enabled")
        super().setUp()

    def tearDown(self):
        self.tmp.cleanup()

    def enabled_gate(self, enabled=True):
        """Patch the real gate path to a mocked root-owned 0600 ALLOW file (tests run unprivileged)."""
        st = unittest.mock.Mock(spec=os.stat_result)
        st.st_mode = stat.S_IFREG | 0o600
        st.st_uid = 0
        lstat = unittest.mock.Mock(return_value=st, side_effect=FileNotFoundError() if not enabled else None)
        opener = unittest.mock.mock_open(read_data=b"ALLOW_REMOTE_DECISIONS\n")
        stack = ExitStack()
        stack.enter_context(unittest.mock.patch.object(client, "REMOTE_DECISIONS_GATE", self.gate))
        stack.enter_context(unittest.mock.patch("os.lstat", lstat))
        stack.enter_context(unittest.mock.patch("builtins.open", opener))
        return stack

    def set_gate(self, mode=0o600, body=b"ALLOW_REMOTE_DECISIONS\n", uid=0, symlink_to=None):
        if symlink_to is not None:
            os.symlink(symlink_to, self.gate)
            return
        with open(self.gate, "wb") as handle:
            handle.write(body)
        os.chmod(self.gate, mode)


class RemoteDecisionGateTests(GateTestMixin):
    def test_gate_absent_is_disabled(self):
        self.assertFalse(client.remote_decisions_enabled(self.gate))

    def test_gate_symlink_is_disabled(self):
        real = os.path.join(self.tmp.name, "real-gate")
        with open(real, "wb") as handle:
            handle.write(b"ALLOW_REMOTE_DECISIONS\n")
        self.set_gate(symlink_to=real)
        self.assertFalse(client.remote_decisions_enabled(self.gate))

    def test_gate_wrong_mode_is_disabled(self):
        st = unittest.mock.Mock(spec=os.stat_result)
        for mode in (0o644, 0o666, 0o777):
            st.st_mode = stat.S_IFREG | mode
            st.st_uid = 0
            with unittest.mock.patch("os.lstat", return_value=st), \
                    unittest.mock.patch("builtins.open", unittest.mock.mock_open(read_data=b"ALLOW_REMOTE_DECISIONS\n")):
                self.assertFalse(client.remote_decisions_enabled(self.gate), oct(mode))

    def test_gate_wrong_content_is_disabled(self):
        st = unittest.mock.Mock(spec=os.stat_result)
        st.st_mode = stat.S_IFREG | 0o600
        st.st_uid = 0
        for body in (b"ALLOW_REMOTE_DECISIONS extra\n", b"SOMETHING_ELSE\n", b""):
            with unittest.mock.patch("os.lstat", return_value=st), \
                    unittest.mock.patch("builtins.open", unittest.mock.mock_open(read_data=body)):
                self.assertFalse(client.remote_decisions_enabled(self.gate), body)

    def test_gate_non_root_owner_is_disabled(self):
        st = unittest.mock.Mock(spec=os.stat_result)
        st.st_mode = stat.S_IFREG | 0o600
        for uid in (1, 1000):
            st.st_uid = uid
            with unittest.mock.patch("os.lstat", return_value=st), \
                    unittest.mock.patch("builtins.open", unittest.mock.mock_open(read_data=b"ALLOW_REMOTE_DECISIONS\n")):
                self.assertFalse(client.remote_decisions_enabled(self.gate), uid)

    def test_gate_valid_root_owned_0600_file_enables_decisions(self):
        st = unittest.mock.Mock(spec=os.stat_result)
        st.st_mode = stat.S_IFREG | 0o600
        st.st_uid = 0
        with unittest.mock.patch("os.lstat", return_value=st), \
                unittest.mock.patch("builtins.open", unittest.mock.mock_open(read_data=b"ALLOW_REMOTE_DECISIONS\n")):
            self.assertTrue(client.remote_decisions_enabled(self.gate))

    def test_gate_never_created_by_the_client(self):
        client.remote_decisions_enabled(self.gate)
        self.assertFalse(os.path.exists(self.gate))


class HandleControlTests(GateTestMixin):
    def reply(self, model, verb, arg=None):
        ev = {"verb": verb, "arg": arg, "reply": queue.Queue()}
        command = client.handle_control(model, ev)
        return ev["reply"].get(timeout=1), command

    def test_status_returns_snapshot_without_secrets(self):
        reply, command = self.reply(pending_model(), "status")
        self.assertIsNone(command)
        self.assertTrue(reply["ok"])
        self.assertEqual(reply["page"], "inbox")
        self.assertEqual(reply["approvals"], 1)
        self.assertEqual(reply["focused_id"], "A-1")
        self.assertTrue(reply["online"])
        self.assertEqual(reply["remote_decisions"], False)
        text = json.dumps(reply)
        self.assertNotIn("token", text.lower())
        self.assertNotIn("http", text.lower())

    def test_snapshot_fields_are_truncated_to_80_chars(self):
        model = pending_model()
        model["data"]["approvals"][0]["action"] = "x" * 200
        reply, _ = self.reply(model, "status")
        self.assertEqual(len(reply["focused_title"]), 80)

    def test_navigation_changes_view_but_never_submits(self):
        for verb, expected_page in [
            ("home", "home"),
            ("status", "inbox"),  # remote 'status' is the snapshot verb; the page is unchanged
            ("inbox", "inbox"),
            ("next", "inbox"),
            ("review", "review"),
            ("detail_next", "review"),
            ("review_back", "inbox"),
        ]:
            model = pending_model()
            if verb in ("detail_next", "review_back"):
                client.apply_action(model, "review")
            reply, command = self.reply(model, verb)
            self.assertTrue(reply["ok"], verb)
            self.assertIsNone(command, verb)
            self.assertEqual(model["page"], expected_page, verb)
            self.assertNotIn("decision", model, verb)
            self.assertEqual(model["data"]["approvals"][0]["revision"], "r1", verb)

    def test_navigation_commands_are_a_subset_that_never_returns_commands(self):
        for verb in client.NAV_VERBS:
            for _ in range(6):
                model = pending_model()
                if verb in ("detail_next", "review_back"):
                    client.apply_action(model, "review")
                self.assertIsNone(client.handle_control(model, {"verb": verb, "arg": None, "reply": queue.Queue()}))

    def test_decisions_refused_without_gate(self):
        model = pending_model()
        client.apply_action(model, "review")
        model["detail"] = 99
        client.apply_action(model, "approve")
        self.assertEqual(model["page"], "review")  # staging did not happen without the gate path check
        for verb in ("approve", "deny", "send"):
            reply, command = self.reply(json.loads(json.dumps(model)), verb)
            self.assertFalse(reply["ok"], verb)
            self.assertIn("disabled", reply["error"], verb)
            self.assertIsNone(command, verb)

    def test_decisions_refused_on_item_mismatch(self):
        from devices.little_lucy.platforms.nebula.native.ui import detail_pages
        with self.enabled_gate():
            model = pending_model()
            client.apply_action(model, "review")
            model["detail"] = len(detail_pages(model["selected"])) - 1
            client.apply_action(model, "approve")
            model["data"]["approvals"][0]["revision"] = "r2"  # changed underneath us
            for verb in ("approve", "deny", "send"):
                reply, command = self.reply(model, verb)
                self.assertFalse(reply["ok"], verb)
                self.assertIn("pending", reply["error"], verb)
                self.assertIsNone(command, verb)

    def test_decisions_refused_when_not_on_pending_approval(self):
        with self.enabled_gate():
            model = pending_model()
            model.pop("selected", None)
            for verb in ("approve", "deny", "send"):
                reply, command = self.reply(model, verb)
                self.assertFalse(reply["ok"], verb)
                self.assertIsNone(command, verb)

    def test_valid_gated_decision_uses_existing_submission_shape(self):
        from devices.little_lucy.platforms.nebula.native.ui import detail_pages
        with self.enabled_gate():
            model = pending_model()
            # The remote flow follows the same canonical path as touch: open the
            # shown card, page to the last detail page, then decide.
            client.apply_action(model, "review")
            model["detail"] = len(detail_pages(model["selected"])) - 1
            reply, command = self.reply(model, "approve")
            self.assertTrue(reply["ok"])
            self.assertIsNone(command)
            self.assertEqual(model["page"], "confirm")
            self.assertEqual(model["decision"], "APPROVED")
            reply, command = self.reply(model, "send")
            self.assertTrue(reply["ok"])
            self.assertEqual(command, {"approval_id": "A-1", "revision": "r1", "decision": "APPROVED"})
            self.assertEqual(set(command), {"approval_id", "revision", "decision"})
            # Remote deny on a fresh review stages DENIED only, never submits.
            model = pending_model()
            client.apply_action(model, "review")
            model["detail"] = len(detail_pages(model["selected"])) - 1
            reply, command = self.reply(model, "deny")
            self.assertTrue(reply["ok"])
            self.assertIsNone(command)
            self.assertEqual(model["decision"], "DENIED")


class ControlClientTests(unittest.TestCase):
    def test_build_request_rules(self):
        self.assertEqual(lucynest_ctl.build_request("status"), b"status\n")
        self.assertEqual(lucynest_ctl.build_request("SEND", " A-1 "), b"send A-1\n")
        with self.assertRaises(ValueError):
            lucynest_ctl.build_request("reboot")
        with self.assertRaises(ValueError):
            lucynest_ctl.build_request("send a\nb")
        with self.assertRaises(ValueError):
            lucynest_ctl.build_request("send", "x" * 300)

    def test_exit_code_1_when_not_root(self):
        if os.geteuid() == 0:
            self.skipTest("running as root; refusal path not applicable")
        result = subprocess.run(
            [sys.executable, str(NATIVE / "lucynest_ctl.py"), "status"],
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("refused", json.loads(result.stdout)["error"])

    def test_exit_code_2_when_socket_unreachable(self):
        with tempfile.TemporaryDirectory() as tmp, \
                unittest.mock.patch("os.geteuid", return_value=0):
            missing = os.path.join(tmp, "missing.sock")
            self.assertEqual(lucynest_ctl.run(["status"], sock_path=missing), 2)

    def test_exit_codes_against_a_live_socket(self):
        with tempfile.TemporaryDirectory() as tmp:
            sock_path = os.path.join(tmp, "control.sock")
            events = queue.Queue()
            stop = threading.Event()
            model = pending_model()
            commands = queue.Queue()
            thread = threading.Thread(
                target=client.control_server_thread,
                args=(events, stop),
                kwargs={"sock_path": sock_path, "allowed_uid": os.getuid()},
                daemon=True,
            )
            thread.start()
            try:
                self.assertTrue(wait_for(sock_path))
                with unittest.mock.patch("os.geteuid", return_value=0), \
                        main_loop_consumer(events, model, commands):
                    self.assertEqual(lucynest_ctl.run(["status"], sock_path=sock_path), 0)
                    # Main-loop-shaped consumer: nav never enqueues; decisions follow the gate.
                    self.assertEqual(lucynest_ctl.run(["next"], sock_path=sock_path), 0)
                    self.assertEqual(lucynest_ctl.run(["approve"], sock_path=sock_path), 1)
                self.assertEqual(commands.qsize(), 0)
                self.assertNotIn("decision", model)
            finally:
                stop.set()
                thread.join(timeout=5)


class MainLoopIntegrationTests(GateTestMixin):
    def test_control_events_reach_the_main_loop_consumer_and_render(self):
        sock_path = os.path.join(self.tmp.name, "control.sock")
        events = queue.Queue()
        stop = threading.Event()
        model = pending_model()
        commands = queue.Queue()
        thread = threading.Thread(
            target=client.control_server_thread,
            args=(events, stop),
            kwargs={"sock_path": sock_path, "allowed_uid": os.getuid()},
            daemon=True,
        )
        thread.start()
        try:
            self.assertTrue(wait_for(sock_path))
            with self.enabled_gate():
                for verb, arg in (
                    ("status", None), ("inbox", None), ("next", None),
                    ("review", None), ("approve", None), ("send", None),
                ):
                    conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    conn.settimeout(5)
                    conn.connect(sock_path)
                    conn.sendall((verb + ((" " + arg) if arg else "") + "\n").encode("utf-8"))
                    kind, ev = events.get(timeout=5)
                    self.assertEqual(kind, "control")
                    command = client.handle_control(model, ev)
                    if command:
                        commands.put(command)
                    reply = json.loads(conn.recv(4096).decode("utf-8"))
                    conn.close()
                    self.assertTrue(reply["ok"], reply)
                # The gated remote decision flowed through the existing commands queue.
                self.assertEqual(commands.qsize(), 1)
                self.assertEqual(commands.get(), {"approval_id": "A-1", "revision": "r1", "decision": "APPROVED"})
                self.assertEqual(model["page"], "sending")
            image, _ = render(model, 1)  # model stays renderable after remote control
            self.assertEqual(image.size, (480, 272))
        finally:
            stop.set()
            thread.join(timeout=5)


class SourceHygieneTests(unittest.TestCase):
    FORBIDDEN = re.compile(r"AF_INET|SOCK_DGRAM|socketserver|http\.server|\.bind\(\s*[\"']|\.bind\(\s*\(\s*[\"']\w+[\"']\s*,\s*\d+")

    def test_new_native_code_has_no_network_listeners(self):
        for name in ("client.py", "lucynest_ctl.py"):
            text = (NATIVE / name).read_text(encoding="utf-8")
            matches = self.FORBIDDEN.findall(text)
            self.assertEqual(matches, [], name)

    def test_native_sources_compile(self):
        for name in ("client.py", "ui.py", "lucynest_ctl.py"):
            py_compile.compile(str(NATIVE / name), doraise=True)


if __name__ == "__main__":
    unittest.main()
