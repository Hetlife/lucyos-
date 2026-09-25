import copy
import unittest

from devices.little_lucy.platforms.nebula.native.client import (
    apply_action,
    map_touch,
    solve_calibration,
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
