# SPDX-FileCopyrightText: Daniel Schaefer 2023 for Framework Computer
# SPDX-License-Identifier: MIT
#
# Keyscan for the Framework Laptop 16 ANSI keyboard.
# Port of the matrix and default keymap from the QMK firmware
# (keyboards/framework/ansi and keyboards/framework/matrix.c).
#
# - Supports multiple keys held at once (modifiers, chords)
# - Fn layer: F1-F12, Insert, Home/End/PgUp/PgDn, Pause, Break, Scroll Lock
# - Fn+Esc toggles Fn lock (F-row sends F1-F12 by default)
# - Fn+Space steps white backlight brightness
# - Caps Lock LED follows the host's Caps Lock state
# - Keys are ignored and the backlight is off while SLEEP# is low
#
# Not supported: Airplane mode key, RGB backlight controls

#
# Requires framework_keyscan.py on the CIRCUITPY drive.

import time
import board
import digitalio
import usb_hid
import pwmio
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.consumer_control_code import ConsumerControlCode
from framework_keyscan import KeyScanner

DEBUG = False
# Print every key reading below this voltage whenever those readings change.
# Useful for tuning the thresholds in framework_keyscan.py. None to disable.
DEBUG_LOW_V = None

# Backlight brightness levels stepped through with Fn+Space (duty cycle 0-1)
BACKLIGHT_LEVELS = [0, 0.25, 0.5, 1.0]

# Special actions
FN = "FN"
FN_LOCK = "FN_LOCK"
BL_STEP = "BL_STEP"


def consumer(code):
    return ("consumer", code)


def combo(*codes):
    return ("combo", codes)


# Key definitions: name -> (base action, Fn layer action, follows Fn lock)
# An action is a Keycode, consumer(...), combo(...), a special action or None.
# Keys that follow Fn lock swap base and Fn layer while Fn lock is on.
KEYS = {
    # F-row
    "ESC": (Keycode.ESCAPE, FN_LOCK, False),
    "MUTE": (consumer(ConsumerControlCode.MUTE), Keycode.F1, True),
    "VOLD": (consumer(ConsumerControlCode.VOLUME_DECREMENT), Keycode.F2, True),
    "VOLU": (consumer(ConsumerControlCode.VOLUME_INCREMENT), Keycode.F3, True),
    "MPRV": (consumer(ConsumerControlCode.SCAN_PREVIOUS_TRACK), Keycode.F4, True),
    "MPLY": (consumer(ConsumerControlCode.PLAY_PAUSE), Keycode.F5, True),
    "MNXT": (consumer(ConsumerControlCode.SCAN_NEXT_TRACK), Keycode.F6, True),
    "BRID": (consumer(ConsumerControlCode.BRIGHTNESS_DECREMENT), Keycode.F7, True),
    "BRIU": (consumer(ConsumerControlCode.BRIGHTNESS_INCREMENT), Keycode.F8, True),
    # Project/switch display: Win+P. Works on Windows and GNOME
    "SCRN": (combo(Keycode.GUI, Keycode.P), Keycode.F9, True),
    # Airplane mode is a HID System Control usage, not available in adafruit_hid
    "AIRP": (None, Keycode.F10, True),
    "PSCR": (Keycode.PRINT_SCREEN, Keycode.F11, True),
    # AL Consumer Control Configuration (media player)
    "MSEL": (consumer(0x0183), Keycode.F12, True),
    "DEL": (Keycode.DELETE, Keycode.INSERT, False),
    # Number row
    "GRV": (Keycode.GRAVE_ACCENT, None, False),
    "1": (Keycode.ONE, None, False),
    "2": (Keycode.TWO, None, False),
    "3": (Keycode.THREE, None, False),
    "4": (Keycode.FOUR, None, False),
    "5": (Keycode.FIVE, None, False),
    "6": (Keycode.SIX, None, False),
    "7": (Keycode.SEVEN, None, False),
    "8": (Keycode.EIGHT, None, False),
    "9": (Keycode.NINE, None, False),
    "0": (Keycode.ZERO, None, False),
    "MINS": (Keycode.MINUS, None, False),
    "EQL": (Keycode.EQUALS, None, False),
    "BSPC": (Keycode.BACKSPACE, None, False),
    # Top letter row
    "TAB": (Keycode.TAB, None, False),
    "Q": (Keycode.Q, None, False),
    "W": (Keycode.W, None, False),
    "E": (Keycode.E, None, False),
    "R": (Keycode.R, None, False),
    "T": (Keycode.T, None, False),
    "Y": (Keycode.Y, None, False),
    "U": (Keycode.U, None, False),
    "I": (Keycode.I, None, False),
    "O": (Keycode.O, None, False),
    "P": (Keycode.P, Keycode.PAUSE, False),
    "LBRC": (Keycode.LEFT_BRACKET, None, False),
    "RBRC": (Keycode.RIGHT_BRACKET, None, False),
    "BSLS": (Keycode.BACKSLASH, None, False),
    # Home row
    "CAPS": (Keycode.CAPS_LOCK, None, False),
    "A": (Keycode.A, None, False),
    "S": (Keycode.S, None, False),
    "D": (Keycode.D, None, False),
    "F": (Keycode.F, None, False),
    "G": (Keycode.G, None, False),
    "H": (Keycode.H, None, False),
    "J": (Keycode.J, None, False),
    "K": (Keycode.K, Keycode.SCROLL_LOCK, False),
    "L": (Keycode.L, None, False),
    "SCLN": (Keycode.SEMICOLON, None, False),
    "QUOT": (Keycode.QUOTE, None, False),
    "ENT": (Keycode.ENTER, None, False),
    # Bottom letter row
    "LSFT": (Keycode.LEFT_SHIFT, None, False),
    "Z": (Keycode.Z, None, False),
    "X": (Keycode.X, None, False),
    "C": (Keycode.C, None, False),
    "V": (Keycode.V, None, False),
    # Break is Ctrl+Pause
    "B": (Keycode.B, combo(Keycode.LEFT_CONTROL, Keycode.PAUSE), False),
    "N": (Keycode.N, None, False),
    "M": (Keycode.M, None, False),
    "COMM": (Keycode.COMMA, None, False),
    "DOT": (Keycode.PERIOD, None, False),
    "SLSH": (Keycode.FORWARD_SLASH, None, False),
    "RSFT": (Keycode.RIGHT_SHIFT, None, False),
    # Bottom row
    "LCTL": (Keycode.LEFT_CONTROL, None, False),
    "FN": (FN, FN, False),
    "LGUI": (Keycode.LEFT_GUI, None, False),
    "LALT": (Keycode.LEFT_ALT, None, False),
    "SPC": (Keycode.SPACE, BL_STEP, False),
    "RALT": (Keycode.RIGHT_ALT, None, False),
    "RCTL": (Keycode.RIGHT_CONTROL, None, False),
    "LEFT": (Keycode.LEFT_ARROW, Keycode.HOME, False),
    "UP": (Keycode.UP_ARROW, Keycode.PAGE_UP, False),
    "DOWN": (Keycode.DOWN_ARROW, Keycode.PAGE_DOWN, False),
    "RGHT": (Keycode.RIGHT_ARROW, Keycode.END, False),
}

# Electrical matrix: MATRIX[row (KSI)][col (KSO)] -> key name
# From the LAYOUT macro in keyboards/framework/ansi/ansi.h
_ = None
# fmt: off
MATRIX = [
    ["C",  "DEL",  "Q",    "RALT", _,      "X",    "V",  "M",  ".",    "RSFT", ",",    _,      "RCTL", "SLSH", "QUOT", _],
    [_,    _,      _,      "LALT", "SPC",  "Z",    "B",  "N",  "DOWN", "LSFT", _,      _,      "LCTL", "UP",   "ENT",  "BRIU"],
    [_,    _,      "FN",   _,      "E",    "VOLD", "G",  "H",  "BSLS", _,      "BRID", _,      _,      "MINS", _,      "RGHT"],
    [_,    "LGUI", "TAB",  _,      "MPRV", "MUTE", "T",  "Y",  "O",    _,      "MNXT", "SCRN", _,      "MSEL", _,      _],
    [_,    _,      "GRV",  _,      "CAPS", "S",    "5",  "6",  "AIRP", _,      "MPLY", _,      _,      "0",    "EQL",  _],
    [_,    _,      "1",    _,      "3",    "2",    "4",  "7",  "9",    _,      "8",    _,      _,      "P",    "BSPC", _],
    [_,    _,      _,      _,      "VOLU", "W",    "R",  "U",  "PSCR", _,      "I",    "LEFT", _,      "LBRC", "RBRC", _],
    [_,    _,      "A",    _,      _,      "ESC",  "F",  "J",  "L",    _,      "K",    _,      _,      "SCLN", "D",    _],
]
# fmt: on
# Short aliases used in the matrix above
KEYS["."] = KEYS["DOT"]
KEYS[","] = KEYS["COMM"]

keyboard = Keyboard(usb_hid.devices)
consumer_control = ConsumerControl(usb_hid.devices)

# SLEEP# pin. Low if the host is sleeping
sleep_pin = digitalio.DigitalInOut(board.SLEEP)
sleep_pin.direction = digitalio.Direction.INPUT

capslock_led = digitalio.DigitalInOut(board.CAPS_LED)
capslock_led.direction = digitalio.Direction.OUTPUT

backlight = pwmio.PWMOut(board.BACKLIGHT, frequency=5000, duty_cycle=0)

scanner = KeyScanner(MATRIX, debug_low_v=DEBUG_LOW_V, debug=DEBUG)


fn_held = False
fn_lock = False
backlight_level = len(BACKLIGHT_LEVELS) - 1
# Action that was sent for each held key, so it's released correctly even if
# Fn changes while the key is held
active_actions = {}


def resolve_action(name):
    (base, fn_action, lockable) = KEYS[name]
    use_fn = fn_held != fn_lock if lockable else fn_held
    action = fn_action if use_fn else base
    # Fall through to base layer for transparent keys
    return action if action is not None or not use_fn else base


def press_action(action):
    global fn_held, fn_lock, backlight_level
    if action is None:
        return
    if action == FN:
        fn_held = True
    elif action == FN_LOCK:
        fn_lock = not fn_lock
        print(f"Fn lock {'on' if fn_lock else 'off'}")
    elif action == BL_STEP:
        backlight_level = (backlight_level + 1) % len(BACKLIGHT_LEVELS)
    elif isinstance(action, tuple) and action[0] == "consumer":
        consumer_control.press(action[1])
    elif isinstance(action, tuple) and action[0] == "combo":
        keyboard.press(*action[1])
    else:
        keyboard.press(action)


def release_action(action):
    global fn_held
    if action is None:
        return
    if action == FN:
        fn_held = False
    elif action in (FN_LOCK, BL_STEP):
        pass
    elif isinstance(action, tuple) and action[0] == "consumer":
        consumer_control.release()
    elif isinstance(action, tuple) and action[0] == "combo":
        keyboard.release(*action[1])
    else:
        keyboard.release(action)


def release_everything():
    global fn_held
    keyboard.release_all()
    consumer_control.release()
    active_actions.clear()
    fn_held = False


while True:
    awake = sleep_pin.value
    backlight.duty_cycle = int(65535 * BACKLIGHT_LEVELS[backlight_level]) if awake else 0
    capslock_led.value = awake and keyboard.led_on(Keyboard.LED_CAPS_LOCK)

    # Ignore keys while the host is asleep, so pressing on the lid
    # (e.g. in a backpack) doesn't wake it up
    if not awake:
        if active_actions:
            release_everything()
        scanner.reset()
        time.sleep(0.1)
        continue

    for pos, pressed in scanner.scan():
        (row, col) = pos
        if pressed:
            action = resolve_action(MATRIX[row][col])
            active_actions[pos] = action
            press_action(action)
        else:
            release_action(active_actions.pop(pos, None))

    time.sleep(0.001)
