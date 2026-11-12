# SPDX-FileCopyrightText: Daniel Schaefer 2023 for Framework Computer
# SPDX-License-Identifier: MIT
#
# Handle button pressed on the numpad.
# Calculator button is not mapped. Not supported by circuitpython
# Backlight 50% on, off and keys ignored if SLEEP# low
# Num Lock LED follows the host's Num Lock state
#
# Requires framework_keyscan.py on the CIRCUITPY drive.

import time
import board
import digitalio
import usb_hid
import pwmio
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from framework_keyscan import KeyScanner

DEBUG = False
# Print every key reading below this voltage whenever those readings change.
# Useful for tuning the thresholds in framework_keyscan.py. None to disable.
DEBUG_LOW_V = None

# Matrix position (row KSI, column KSO) -> (x, y) position in NUMPAD_KEYMAP
MATRIX = [
    [(0, 1), (0, 2), (0, 3), (0, 4), (1, 1), (1, 2), (1, 3), (1, 4)],
    [(0, 5), (2, 1), (2, 2), (2, 3), (2, 4), (2, 5), (3, 1), (3, 3)],
    [(3, 5), (0, 0), (1, 0), None, (3, 0), (3, 2), (3, 4), (1, 5)],
    [None, None, None, None, (2, 0), None, None, None],
]
# Physical layout. Tall keys (+, Enter) and the wide 0 occupy two cells.
NUMPAD_KEYMAP = [
    # circuitpython doesn't have calculator keycode
    [Keycode.ESCAPE, None, Keycode.EQUALS, Keycode.BACKSPACE],
    [
        Keycode.KEYPAD_NUMLOCK,
        Keycode.KEYPAD_FORWARD_SLASH,
        Keycode.KEYPAD_ASTERISK,
        Keycode.KEYPAD_MINUS,
    ],
    [Keycode.KEYPAD_SEVEN, Keycode.KEYPAD_EIGHT, Keycode.KEYPAD_NINE, Keycode.KEYPAD_PLUS],
    [Keycode.KEYPAD_FOUR, Keycode.KEYPAD_FIVE, Keycode.KEYPAD_SIX, Keycode.KEYPAD_PLUS],
    [Keycode.KEYPAD_ONE, Keycode.KEYPAD_TWO, Keycode.KEYPAD_THREE, Keycode.KEYPAD_ENTER],
    [Keycode.KEYPAD_ZERO, Keycode.KEYPAD_ZERO, Keycode.KEYPAD_PERIOD, Keycode.KEYPAD_ENTER],
]
keyboard = Keyboard(usb_hid.devices)

# SLEEP# pin. Low if the host is sleeping
sleep_pin = digitalio.DigitalInOut(board.SLEEP)
sleep_pin.direction = digitalio.Direction.INPUT

numlock_led = digitalio.DigitalInOut(board.CAPS_LED)
numlock_led.direction = digitalio.Direction.OUTPUT

backlight = pwmio.PWMOut(board.BACKLIGHT, frequency=5000, duty_cycle=0)

held = set()

scanner = KeyScanner(MATRIX, debug_low_v=DEBUG_LOW_V, debug=DEBUG)

while True:
    awake = sleep_pin.value
    backlight.duty_cycle = int(65535 / 2) if awake else 0
    numlock_led.value = awake and keyboard.led_on(Keyboard.LED_NUM_LOCK)

    # Ignore keys while the host is asleep
    if not awake:
        if held:
            keyboard.release_all()
            held.clear()
        scanner.reset()
        time.sleep(0.1)
        continue

    for (row, col), pressed in scanner.scan():
        (x, y) = MATRIX[row][col]
        code = NUMPAD_KEYMAP[y][x]
        if code is None:
            continue
        if pressed:
            print(f"Pressed {code} (KSO{col}, KSI{row})")
            keyboard.press(code)
            held.add(code)
        else:
            keyboard.release(code)
            held.discard(code)

    time.sleep(0.001)
