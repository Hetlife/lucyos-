import unittest
from pathlib import Path

from tests.base import AionTest
from aion_core import security


class TestSecretDetection(unittest.TestCase):
    def test_detects_common_credential_shapes(self):
        cases = {
            "sk-ant-api03-AbCdEfGhIjKlMnOpQrStUvWx": "anthropic_key",
            "ghp_AbCdEfGhIjKlMnOpQrStUvWxYz012345": "github_token",
            "AKIAIOSFODNN7EXAMPLE": "aws_access_key",
            "rzp_live_ABCDEFGH1234": "razorpay_key",
            "password: correcthorsebattery": "assigned_secret",
            "my otp is 483920": "otp_phrase",
        }
        for text, expected in cases.items():
            kinds = [f["kind"] for f in security.scan_text(text)]
            self.assertIn(expected, kinds, f"missed {expected} in {text!r}")

    def test_does_not_flag_ordinary_owner_messages(self):
        for text in ["APPROVE A-142", "status", "money", "deny A-101",
                     "what happened today", "API_KEY=<your-key-here>",
                     "the invoice is 2024-08-11 for 45000"]:
            self.assertEqual(security.scan_text(text), [], f"false positive on {text!r}")

    def test_redaction_removes_the_value(self):
        text = "token ghp_AbCdEfGhIjKlMnOpQrStUvWxYz012345 ok"
        out = security.redact(text)
        self.assertNotIn("ghp_AbCdEfGhIjKlMnOpQrStUvWxYz012345", out)
        self.assertIn("[REDACTED]", out)

    def test_assert_clean_raises(self):
        with self.assertRaises(security.SecretLeak):
            security.assert_clean("AWS key AKIAIOSFODNN7EXAMPLE", "whatsapp reply")

    def test_card_number_luhn_filter(self):
        self.assertEqual(security.scan_text("ref 1234567890123456"), [])
        self.assertTrue(security.scan_text("card 4242424242424242"))


class TestPathScan(AionTest):
    def test_scan_paths_finds_planted_secret(self):
        f = self.tmp / "leak.md"
        f.write_text("key: ghp_AbCdEfGhIjKlMnOpQrStUvWxYz012345\n")
        found = security.scan_paths(self.tmp)
        self.assertTrue(any(r["file"].endswith("leak.md") for r in found))

    def test_scan_skips_private_state(self):
        p = self.tmp / "private_state" / "secrets.env"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("GITHUB_TOKEN=ghp_AbCdEfGhIjKlMnOpQrStUvWxYz012345\n")
        self.assertEqual(security.scan_paths(self.tmp), [])


if __name__ == "__main__":
    unittest.main()
