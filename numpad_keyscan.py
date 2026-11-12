# SPDX-FileCopyrightText: Daniel Schaefer 2023 for Framework Computer
# SPDX-License-Identifier: MIT
#
# Handle button pressed on the numpad.
# Calculator button is not mapped. Not supported by circuitpython
# Backlight 50% on, of off if SLEEP# low

import time
import board
import digitalio
import analogio
import usb_hid
import pwmio
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

MATRIX_COLS = 8
MATRIX_ROWS = 4

# Pressed keys read ~0.0-0.2V. Idle keys settle at ~2.4-3.3V, but neighbors of a
# held key can dip to ~1.5V, so keep the threshold well below that.
# (Values measured on the macropad, which uses the same matrix circuit.)
ADC_THRESHOLD = 1.0
# The rows read low right after the pins are configured until they charge up.
# Ignore scans during this time to avoid phantom key presses.
STARTUP_SETTLE_S = 1.0
DEBUG = False

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

# Set up analog MUX pins
mux_enable = sleep_pin = digitalio.DigitalInOut(board.MUX_ENABLE)
mux_enable.direction = digitalio.Direction.OUTPUT
mux_enable.value = False  # Low to enable it
mux_a = sleep_pin = digitalio.DigitalInOut(board.MUX_A)
mux_a.direction = digitalio.Direction.OUTPUT
mux_b = sleep_pin = digitalio.DigitalInOut(board.MUX_B)
mux_b.direction = digitalio.Direction.OUTPUT
mux_c = sleep_pin = digitalio.DigitalInOut(board.MUX_C)
mux_c.direction = digitalio.Direction.OUTPUT

# Set up KSO pins
kso_pins = [
    digitalio.DigitalInOut(x)
    for x in [
        # KSO0 - KSO7 for Keyboards and Numpad
        board.KSO0,
        board.KSO1,
        board.KSO2,
        board.KSO3,
        board.KSO4,
        board.KSO5,
        board.KSO6,
        board.KSO7,
        # KSO8 - KSO15 for Keyboards only
        board.KSO8,
        board.KSO9,
        board.KSO10,
        board.KSO11,
        board.KSO12,
        board.KSO13,
        board.KSO14,
        board.KSO15,
    ]
]
for kso in kso_pins:
    kso.direction = digitalio.Direction.OUTPUT
adc_in = analogio.AnalogIn(board.ANALOG_IN)

# Signal boot done
boot_done = sleep_pin = digitalio.DigitalInOut(board.BOOT_DONE)
boot_done.direction = digitalio.Direction.OUTPUT
boot_done.value = False


def mux_select_row(row):
    index = 0
    if row == 0:
        index = 2
    elif row == 1:
        index = 0
    elif row == 2:
        index = 1
    else:
        index = row

    mux_a.value = index & 0x01
    mux_b.value = index & 0x02
    mux_c.value = index & 0x04


def drive_col(col, value):
    kso_pins[col].value = value


def to_voltage(adc_sample):
    return (adc_sample * 3.3) / 65536


def matrix_scan():
    matrix_pos = None
    for col in range(MATRIX_COLS):
        drive_col(col, True)

    for col in range(MATRIX_COLS):
        drive_col(col, False)

        for row in range(MATRIX_ROWS):
            mux_select_row(row)

            voltage = to_voltage(adc_in.value)
            if DEBUG:
                print(f"{col}:{row}: {voltage}V")

            if voltage < ADC_THRESHOLD:
                if DEBUG:
                    print(f"Pressed {col}:{row}")
                matrix_pos = (col, row)

                # TODO: Handle debounce in a different way
                # If we break here we can only ever handle a single keypress at once
                if matrix_pos:
                    break

        drive_col(col, True)
    if DEBUG:
        print()
    return matrix_pos

# SLEEP# pin. Low if the host is sleeping
sleep_pin = digitalio.DigitalInOut(board.SLEEP)
sleep_pin.direction = digitalio.Direction.INPUT

backlight = pwmio.PWMOut(board.BACKLIGHT, frequency=5000, duty_cycle=0)

prev_matrix_pos = None
debounce = 0
color = 0  # 0 Blue, 1 Green, 2 Red

# Keep scanning (and discarding results) until the row lines have charged up
settle_end = time.monotonic() + STARTUP_SETTLE_S
while time.monotonic() < settle_end:
    matrix_scan()

while True:
    backlight.duty_cycle = int(65535 / 2) if sleep_pin.value else 0
    matrix_pos = matrix_scan()
    # Ignore positions in the matrix that have no key
    if matrix_pos and MATRIX[matrix_pos[1]][matrix_pos[0]] is None:
        matrix_pos = None

    if not matrix_pos:
        debounce = 0
    if matrix_pos and matrix_pos == prev_matrix_pos:
        debounce += 1
        # print(f"Debounce {debounce}")

    if matrix_pos and (matrix_pos != prev_matrix_pos or debounce > 10 or debounce == 0):
        debounce = 0
        (col, row) = matrix_pos
        (x, y) = MATRIX[row][col]
        code = NUMPAD_KEYMAP[y][x]
        if code:
            print(f"Pressed {code} ({col}, {row})")

            keyboard.press(code)
            keyboard.release_all()
    prev_matrix_pos = matrix_pos

    time.sleep(0.01)
