import unittest

from devices.little_lucy.platforms.nebula.native.hid import (
    HidOutput,
    MockTransport,
    keyboard_report,
    mouse_report,
    resolve_key,
)


class HidTests(unittest.TestCase):
    def test_keyboard_report_layout_and_modifier_bits(self):
        self.assertEqual(
            keyboard_report(("ctrl", "shift"), ("a",)),
            bytes([0x03, 0x00, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00]),
        )

    def test_duplicate_keys_collapse_and_too_many_distinct_keys_reject(self):
        self.assertEqual(
            keyboard_report((), ("a", "a", "b")),
            bytes([0x00, 0x00, 0x04, 0x05, 0x00, 0x00, 0x00, 0x00]),
        )
        with self.assertRaises(ValueError):
            keyboard_report((), ("a", "b", "c", "d", "e", "f", "g"))

    def test_unknown_key_rejects(self):
        with self.assertRaises(ValueError):
            keyboard_report((), ("nope",))

    def test_mouse_report_clamps_and_sets_buttons(self):
        self.assertEqual(mouse_report(("left", "right"), 200, -200, 5), bytes([0x03, 0x7F, 0x81, 0x05]))

    def test_mock_transport_records_exact_bytes(self):
        transport = MockTransport()
        self.assertEqual(transport.write(b"abc"), 3)
        self.assertEqual(transport.reports, [b"abc"])
        transport.close()
        self.assertTrue(transport.closed)

    def test_press_then_release_and_release_all_clear_state(self):
        transport = MockTransport()
        hid = HidOutput(transport)
        hid.press(("ctrl",), ("a",))
        hid.release()
        self.assertEqual(transport.reports[0], bytes([0x01, 0x00, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00]))
        self.assertEqual(transport.reports[1], bytes([0x00] * 8))

        hid.press(("shift",), ("b",))
        hid.release_all()
        self.assertEqual(transport.reports[-2], bytes([0x00] * 8))
        self.assertEqual(transport.reports[-1], bytes([0x00, 0x00, 0x00, 0x00]))
        self.assertEqual(hid.held_modifiers, [])
        self.assertEqual(hid.held_keys, [])
        self.assertEqual(hid.held_buttons, [])

    def test_resolve_key_is_case_insensitive_and_rejects_unknown(self):
        self.assertEqual(resolve_key("A"), resolve_key("a"))
        self.assertEqual(resolve_key("F12"), 0x45)
        with self.assertRaises(ValueError):
            resolve_key("unknown")


if __name__ == "__main__":
    unittest.main()
