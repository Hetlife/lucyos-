import copy
import os
import unittest

from devices.little_lucy.platforms.nebula.native.client import (
    TouchDecoder,
    apply_action,
    map_touch,
    require_device_runtime,
    solve_calibration,
    validate_connection_config,
    validate_status,
)
from devices.little_lucy.platforms.nebula.native.ui import detail_pages, render


class NativeSourceTests(unittest.TestCase):
    def test_rotated_calibration(self):
        raw = [(3500, 400), (3500, 3600), (500, 2000)]
        matrix = solve_calibration(raw)
        for point, target in zip(raw, [(40, 65), (440, 65), (240, 195)]):
            actual = map_touch(matrix, *point)
            for got, expected in zip(actual, target):
                self.assertAlmostEqual(got, expected)
        with self.assertRaises(ValueError):
            solve_calibration([(1, 1)] * 3)

    def test_touch_decoder_accepts_standard_and_mt_event_order(self):
        decoder = TouchDecoder()
        # BTN_TOUCH arrives before coordinates and SYN.
        self.assertIsNone(decoder.feed(1, 330, 1, now=1.0))
        decoder.feed(3, 53, 100, now=1.01)
        decoder.feed(3, 54, 200, now=1.02)
        self.assertIsNone(decoder.feed(0, 0, 0, now=1.03))
        self.assertEqual(decoder.feed(1, 330, 0, now=1.04), ((100, 200), (100, 200)))

        # Some drivers report SYN before the final coordinates.
        decoder = TouchDecoder()
        decoder.feed(1, 330, 1, now=2.0)
        decoder.feed(0, 0, 0, now=2.01)
        decoder.feed(3, 0, 120, now=2.02)
        decoder.feed(3, 1, 220, now=2.03)
        self.assertEqual(decoder.feed(1, 330, 0, now=2.04), ((120, 220), (120, 220)))

    def test_touch_decoder_preserves_the_release_endpoint(self):
        decoder = TouchDecoder()
        decoder.feed(1, 330, 1, now=4.0)
        decoder.feed(3, 0, 10, now=4.01)
        decoder.feed(3, 1, 10, now=4.02)
        decoder.feed(3, 0, 100, now=4.03)
        decoder.feed(3, 1, 100, now=4.04)
        self.assertEqual(decoder.feed(1, 330, 0, now=4.05), ((10, 10), (100, 100)))

    def test_touch_decoder_requires_a_button_release(self):
        decoder = TouchDecoder()
        decoder.feed(3, 0, 10, now=3.0)
        decoder.feed(3, 1, 20, now=3.01)
        self.assertIsNone(decoder.feed(0, 0, 0, now=3.02))
        self.assertIsNone(decoder.feed(1, 330, 1, now=3.03))
        self.assertEqual(decoder.feed(1, 330, 0, now=3.04), ((10, 20), (10, 20)))

    def test_connection_config_requires_https_and_rejects_empty_auth(self):
        url, token = validate_connection_config({"url": "https://192.168.31.125:18792", "token": "pairing-value"})
        self.assertEqual(url, "https://192.168.31.125:18792")
        self.assertEqual(token, "pairing-value")
        with self.assertRaises(ValueError):
            validate_connection_config({"url": "http://192.168.31.125:18792", "token": "pairing-value"})
        with self.assertRaises(ValueError):
            validate_connection_config({"url": "https://192.168.31.125:18792", "token": ""})

    def test_status_validation_rejects_unknown_shape(self):
        value = {
            "as_of": 1.0, "source": "LucyOS / this laptop", "counts": {},
            "active": [], "approvals": [], "paused": False, "safe_mode": False,
        }
        self.assertEqual(validate_status(value), value)
        with self.assertRaises(ValueError):
            validate_status({**value, "source": "other"})
        with self.assertRaises(ValueError):
            validate_status({**value, "approvals": {}})

    def test_device_runtime_requires_explicit_opt_in(self):
        old = dict(os.environ)
        try:
            os.environ.pop("LUCY_NEST_RUNTIME", None)
            os.environ.pop("LUCY_NEST_DISPLAY_OWNER", None)
            with self.assertRaises(SystemExit):
                require_device_runtime()
        finally:
            os.environ.clear()
            os.environ.update(old)

    def test_approval_requires_review_confirmation_and_freshness(self):
        card = {"approval_id": "A-1", "action": "Test", "revision": "one"}
        model = {
            "page": "inbox",
            "online": True,
            "data": {"approvals": [card]},
            "index": 0,
        }
        self.assertIsNone(apply_action(model, "send"))
        apply_action(model, "review")
        model["detail"] = len(detail_pages(card)) - 1
        apply_action(model, "approve")
        self.assertEqual(model["page"], "confirm")

        offline = copy.deepcopy(model)
        offline["online"] = False
        self.assertIsNone(apply_action(offline, "send"))

        stale = copy.deepcopy(model)
        stale["data"]["approvals"][0]["revision"] = "two"
        self.assertIsNone(apply_action(stale, "send"))
        self.assertEqual(stale["page"], "result")

        command = apply_action(model, "send")
        self.assertEqual(command["approval_id"], "A-1")
        self.assertIsNone(apply_action(model, "send"))

    def test_screens_are_native_size(self):
        for page in ("home", "status", "inbox", "calibrate", "result", "sending"):
            image, _ = render({"page": page, "online": False}, 12)
            self.assertEqual(image.size, (480, 272))


if __name__ == "__main__":
    unittest.main()
