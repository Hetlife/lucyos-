"""Nebula HID report builders.

This module only builds report bytes and writes them to an injected transport.
It does not open devices or touch platform-specific runtime state.
"""


MODIFIERS = {
    "ctrl": 0x01,
    "leftctrl": 0x01,
    "shift": 0x02,
    "leftshift": 0x02,
    "alt": 0x04,
    "leftalt": 0x04,
    "gui": 0x08,
    "super": 0x08,
    "leftgui": 0x08,
    "rightctrl": 0x10,
    "rightshift": 0x20,
    "rightalt": 0x40,
    "rightgui": 0x80,
}


KEYCODES = {
    "a": 0x04, "b": 0x05, "c": 0x06, "d": 0x07, "e": 0x08, "f": 0x09,
    "g": 0x0A, "h": 0x0B, "i": 0x0C, "j": 0x0D, "k": 0x0E, "l": 0x0F,
    "m": 0x10, "n": 0x11, "o": 0x12, "p": 0x13, "q": 0x14, "r": 0x15,
    "s": 0x16, "t": 0x17, "u": 0x18, "v": 0x19, "w": 0x1A, "x": 0x1B,
    "y": 0x1C, "z": 0x1D,
    "1": 0x1E, "2": 0x1F, "3": 0x20, "4": 0x21, "5": 0x22,
    "6": 0x23, "7": 0x24, "8": 0x25, "9": 0x26, "0": 0x27,
    "enter": 0x28,
    "escape": 0x29,
    "backspace": 0x2A,
    "tab": 0x2B,
    "space": 0x2C,
    "minus": 0x2D,
    "equal": 0x2E,
    "bracketleft": 0x2F,
    "bracketright": 0x30,
    "backslash": 0x31,
    "semicolon": 0x33,
    "quote": 0x34,
    "grave": 0x35,
    "comma": 0x36,
    "period": 0x37,
    "slash": 0x38,
    "capslock": 0x39,
    "f1": 0x3A, "f2": 0x3B, "f3": 0x3C, "f4": 0x3D, "f5": 0x3E, "f6": 0x3F,
    "f7": 0x40, "f8": 0x41, "f9": 0x42, "f10": 0x43, "f11": 0x44, "f12": 0x45,
    "printscreen": 0x46,
    "scrolllock": 0x47,
    "pause": 0x48,
    "insert": 0x49,
    "home": 0x4A,
    "pageup": 0x4B,
    "delete": 0x4C,
    "end": 0x4D,
    "pagedown": 0x4E,
    "right": 0x4F,
    "left": 0x50,
    "down": 0x51,
    "up": 0x52,
    "numlock": 0x53,
    "kp_enter": 0x58,
    "leftctrl": 0xE0,
    "leftshift": 0xE1,
    "leftalt": 0xE2,
    "leftgui": 0xE3,
    "rightctrl": 0xE4,
    "rightshift": 0xE5,
    "rightalt": 0xE6,
    "rightgui": 0xE7,
}


def resolve_key(name):
    key = str(name).lower()
    if key not in KEYCODES:
        raise ValueError("unknown key: %r" % (name,))
    return KEYCODES[key]


def _resolve_modifier(value):
    if isinstance(value, int):
        return value & 0xFF
    key = str(value).lower()
    if key not in MODIFIERS:
        raise ValueError("unknown modifier: %r" % (value,))
    return MODIFIERS[key]


def _resolve_button(value):
    key = str(value).lower()
    if key == "left":
        return 0x01
    if key == "right":
        return 0x02
    if key == "middle":
        return 0x04
    raise ValueError("unknown button: %r" % (value,))


def _clamp_signed_byte(value):
    value = int(value)
    if value < -127:
        return -127
    if value > 127:
        return 127
    return value


def keyboard_report(modifiers, keys):
    modifier_byte = 0
    for modifier in modifiers:
        modifier_byte |= _resolve_modifier(modifier)

    keycodes = []
    seen = set()
    for key in keys:
        code = key if isinstance(key, int) else resolve_key(key)
        if code not in seen:
            seen.add(code)
            keycodes.append(code)
    if len(keycodes) > 6:
        raise ValueError("too many distinct keys")
    return bytes([modifier_byte, 0x00] + keycodes + [0x00] * (6 - len(keycodes)))


def mouse_report(buttons, dx, dy, wheel):
    button_byte = 0
    for button in buttons:
        button_byte |= _resolve_button(button)
    return bytes([
        button_byte,
        _clamp_signed_byte(dx) & 0xFF,
        _clamp_signed_byte(dy) & 0xFF,
        _clamp_signed_byte(wheel) & 0xFF,
    ])


class MockTransport:
    def __init__(self):
        self.reports = []
        self.closed = False

    def write(self, data):
        self.reports.append(bytes(data))
        return len(data)

    def close(self):
        self.closed = True


class HidOutput:
    def __init__(self, transport):
        self.transport = transport
        self.held_modifiers = []
        self.held_keys = []
        self.held_buttons = []

    def _write_keyboard(self, modifiers, keys):
        report = keyboard_report(modifiers, keys)
        self.transport.write(report)

    def _write_mouse(self, buttons, dx, dy, wheel):
        report = mouse_report(buttons, dx, dy, wheel)
        self.transport.write(report)

    def press(self, modifiers=(), keys=()):
        self.held_modifiers = list(modifiers)
        self.held_keys = list(keys)
        self._write_keyboard(self.held_modifiers, self.held_keys)

    def release(self):
        self.held_modifiers = []
        self.held_keys = []
        self._write_keyboard((), ())

    def move(self, dx, dy):
        self._write_mouse((), dx, dy, 0)

    def click(self, button='left'):
        self.held_buttons = [button]
        self._write_mouse(self.held_buttons, 0, 0, 0)
        self.held_buttons = []
        self._write_mouse((), 0, 0, 0)

    def scroll(self, amount):
        self._write_mouse((), 0, 0, amount)

    def release_all(self):
        self.held_modifiers = []
        self.held_keys = []
        self.held_buttons = []
        self._write_keyboard((), ())
        self._write_mouse((), 0, 0, 0)
