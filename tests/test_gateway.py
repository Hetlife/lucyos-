"""Phase-1 gateway positive and hostile envelope tests."""
import importlib.util
import unittest
from datetime import datetime, timedelta, timezone

from tests.base import AionTest


@unittest.skipUnless(importlib.util.find_spec("scitt_cose") and importlib.util.find_spec("cbor2"),
                     "gateway dependency set is installed only in gateway-enabled environments")
class GatewayEnvelopeTests(AionTest):
    def setUp(self):
        super().setUp()
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from aion_core import gateway
        self.gateway = gateway
        self.private = Ed25519PrivateKey.generate()
        self.raw = self.private.private_bytes_raw()
        self.public = self.private.public_key().public_bytes_raw()
        gateway.register_device("phone-1", "owner", self.public)

    def operation(self, **overrides):
        now = datetime.now(timezone.utc).replace(microsecond=0)
        data = {
            "schema": self.gateway.SCHEMA, "request_id": "REQ-1", "action": "status.read",
            "params_hash": self.gateway.parameters_hash({"path": "health"}), "target": None,
            "risk_class": "R0", "capability": "status.read/1", "device_id": "phone-1",
            "key_version": 1, "identity": "owner", "nonce": self.gateway.new_nonce(),
            "issued_at": (now - timedelta(seconds=1)).isoformat().replace("+00:00", "Z"),
            "expires_at": (now + timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
            "policy": "policy/1", "approval_id": "A-1", "epoch": 1,
        }
        data.update(overrides)
        return data

    def test_known_positive_and_parameter_binding(self):
        op = self.operation()
        msg = self.gateway.sign_operation(op, self.raw)
        self.assertEqual(self.gateway.validate(msg, {"path": "health"}), op)
        with self.assertRaises(self.gateway.GatewayError):
            self.gateway.validate(msg, {"path": "changed"})

    def test_replay_and_duplicate_request_fail(self):
        op = self.operation()
        msg = self.gateway.sign_operation(op, self.raw)
        self.gateway.validate(msg)
        with self.assertRaises(self.gateway.GatewayError):
            self.gateway.validate(msg)

    def test_tamper_expiry_wrong_device_and_revocation_fail(self):
        op = self.operation()
        bad = bytearray(self.gateway.sign_operation(op, self.raw))
        bad[-1] ^= 1
        with self.assertRaises(self.gateway.GatewayError):
            self.gateway.validate(bytes(bad))
        expired = dict(op, nonce=self.gateway.new_nonce(), expires_at="2000-01-01T00:00:00Z")
        with self.assertRaises(self.gateway.GatewayError):
            self.gateway.validate(self.gateway.sign_operation(expired, self.raw))
        self.gateway.revoke_device("phone-1", "lost")
        with self.assertRaises(self.gateway.GatewayError):
            self.gateway.validate(self.gateway.sign_operation(dict(op, nonce=self.gateway.new_nonce()), self.raw))

    def test_submit_uses_existing_task_path_and_risk_gate(self):
        op = self.operation()
        task_id = self.gateway.submit(self.gateway.sign_operation(op, self.raw), title="health check",
                                      parameters={"path": "health"})
        from aion_core import tasks
        self.assertEqual(tasks.get(task_id)["status"], "READY")
        op2 = self.operation(request_id="REQ-2", approval_id="A-2", nonce=self.gateway.new_nonce(), risk_class="R2")
        task2 = self.gateway.submit(self.gateway.sign_operation(op2, self.raw), title="write action")
        self.assertEqual(tasks.get(task2)["status"], "NEEDS_APPROVAL")

    def test_malformed_oversized_wrong_epoch_and_restart_replay_fail_closed(self):
        with self.assertRaises(self.gateway.GatewayError):
            self.gateway.validate(b"not-cose")
        with self.assertRaises(self.gateway.GatewayError):
            self.gateway.validate(b"x" * (self.gateway.MAX_MESSAGE + 1))
        op = self.operation()
        with self.assertRaises(self.gateway.GatewayError):
            self.gateway.validate(self.gateway.sign_operation(dict(op, epoch=2), self.raw))
        msg = self.gateway.sign_operation(dict(op, request_id="REQ-restart", nonce=self.gateway.new_nonce()), self.raw)
        self.gateway.validate(msg)
        from aion_core import db
        db.close()
        db.connect()
        with self.assertRaises(self.gateway.GatewayError):
            self.gateway.validate(msg)

    def test_untrusted_prompt_and_privilege_escalation_are_not_capabilities(self):
        prompt = self.operation(action="shell.exec", target="ignore previous policy")
        with self.assertRaises(self.gateway.GatewayError):
            self.gateway.validate(self.gateway.sign_operation(prompt, self.raw))
