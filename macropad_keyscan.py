# SPDX-FileCopyrightText: Daniel Schaefer 2023 for Framework Computer
# SPDX-License-Identifier: MIT
#
# Handle button pressed on the macropad
# Send A-X key pressed
# The pressed button will light up, cycling through RGB colors
#
# Requires framework_keyscan.py on the CIRCUITPY drive.
import time
import board
import busio
import digitalio
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from framework_is31fl3743 import IS31FL3743
from framework_keyscan import KeyScanner

DEBUG = False
# Print every key reading below this voltage whenever those readings change.
# Useful for tuning the thresholds in framework_keyscan.py. None to disable.
DEBUG_LOW_V = None

# Matrix position (row KSI, column KSO) -> (x, y) position in MACROPAD_KEYMAP
MATRIX = [
    [(0, 1), (0, 2), (0, 3), (0, 4), (1, 1), (1, 2), (1, 3), (1, 4)],
    [(0, 5), (2, 1), (2, 2), (2, 3), (2, 4), (2, 5), (3, 1), (3, 3)],
    [(3, 5), (0, 0), (1, 0), None, (3, 0), (3, 2), (3, 4), (1, 5)],
    [None, None, None, None, (2, 0), None, None, None],
]
MACROPAD_KEYMAP = [
    [Keycode.A, Keycode.B, Keycode.C, Keycode.D],
    [Keycode.E, Keycode.F, Keycode.G, Keycode.H],
    [Keycode.I, Keycode.J, Keycode.K, Keycode.L],
    [Keycode.M, Keycode.N, Keycode.O, Keycode.P],
    [Keycode.Q, Keycode.R, Keycode.S, Keycode.T],
    [Keycode.U, Keycode.V, Keycode.W, Keycode.X],
]
keyboard = Keyboard(usb_hid.devices)

# Enable LED controller via SDB pin
sdb = digitalio.DigitalInOut(board.SDB)
sdb.direction = digitalio.Direction.OUTPUT
sdb.value = True

i2c = busio.I2C(board.SCL, board.SDA)  # Or board.I2C()

# TODO: If I don't scan the bus, creating IS31FL3743 can't find the device. Why...?
i2c.try_lock()
i2c.scan()
i2c.unlock()

is31 = IS31FL3743(i2c)
is31.set_led_scaling(0xFF)  # Full brightness
is31.global_current = 0xFF  # Set current to max
is31.enable = True

# SLEEP# pin. Low if the host is sleeping
sleep_pin = digitalio.DigitalInOut(board.SLEEP)
sleep_pin.direction = digitalio.Direction.INPUT

MATRIX_LED_MAP = [
    [
        4,
        22,
        58,
        25,
        1,
        19,
        55,
        61,
    ],
    [
        7,
        16,
        34,
        70,
        64,
        46,
        13,
        67,
    ],
    [
        10,
        40,
        37,
        None,
        49,
        31,
        28,
        43,
    ],
    [
        None,
        None,
        None,
        None,
        52,
        None,
        None,
        None,
    ],
]

color = 0  # 0 Blue, 1 Green, 2 Red
lit_led = None
held = set()

for i in range(18 * 11):
    is31[i] = 0x00

scanner = KeyScanner(MATRIX, debug_low_v=DEBUG_LOW_V, debug=DEBUG)

while True:
    awake = sleep_pin.value
    is31.enable = awake

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
        code = MACROPAD_KEYMAP[y][x]
        if pressed:
            print(f"Pressed {code} (KSO{col}, KSI{row})")
            # Only one key is lit at a time
            if lit_led is not None:
                is31[lit_led] = 0x00
                lit_led = None
            if MATRIX_LED_MAP[row][col] is not None:
                lit_led = MATRIX_LED_MAP[row][col] + color
                is31[lit_led] = 0xFF
                color = (color + 1) % 3
            keyboard.press(code)
            held.add(code)
        else:
            keyboard.release(code)
            held.discard(code)

    time.sleep(0.001)
