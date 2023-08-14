# SPDX-FileCopyrightText: Daniel Schaefer 2023 for Framework Computer
# SPDX-License-Identifier: MIT
#
# Handle button pressed on the macropad
# Send A-X key pressed
# The pressed button will light up, cycling through RGB colors
import time
import board
import busio
import digitalio
import analogio
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from framework_is31fl3743 import IS31FL3743

MATRIX_COLS = 8
MATRIX_ROWS = 4

ADC_THRESHOLD = 2.9
DEBUG = False

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

# Set unused pins to input to avoid interfering. They're hooked up to rows 5 and 6
gp6 = sleep_pin = digitalio.DigitalInOut(board.GP6)
gp6.direction = digitalio.Direction.INPUT
gp7 = sleep_pin = digitalio.DigitalInOut(board.GP7)
gp7.direction = digitalio.Direction.INPUT

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
adc_in = analogio.AnalogIn(board.GP28)

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


# Enable LED controller via SDB pin
sdb = digitalio.DigitalInOut(board.GP29)
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
sleep_pin = digitalio.DigitalInOut(board.GP0)
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

prev_matrix_pos = None
debounce = 0
color = 0  # 0 Blue, 1 Green, 2 Red
while True:
    is31.enable = sleep_pin.value
    matrix_pos = matrix_scan()

    if not matrix_pos:
        debounce = 0
    if matrix_pos and matrix_pos == prev_matrix_pos:
        debounce += 1
        # print(f"Debounce {debounce}")

    if matrix_pos and (matrix_pos != prev_matrix_pos or debounce > 10 or debounce == 0):
        debounce = 0
        (col, row) = matrix_pos
        (x, y) = MATRIX[row][col]
        code = MACROPAD_KEYMAP[y][x]
        if code:
            print(f"Pressed {code} ({col}, {row})")

            for i in range(18 * 11):
                is31[i] = 0x00
            if MATRIX_LED_MAP[row][col]:
                is31[MATRIX_LED_MAP[row][col] + color] = 0xFF
                color = (color + 1) % 3
            keyboard.press(code)
            keyboard.release_all()
    prev_matrix_pos = matrix_pos

    time.sleep(0.01)
