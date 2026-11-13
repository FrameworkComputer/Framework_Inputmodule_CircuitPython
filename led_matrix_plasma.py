# SPDX-FileCopyrightText: 2026 Framework Computer Inc
# SPDX-License-Identifier: MIT
#
# Animated plasma for the Framework Laptop 16 LED Matrix (9 x 34).
# Adapted from plasma_frame in inputmodule-rs/inputmodule-control/src/inputmodule.rs.
#
# Copy this file to the CIRCUITPY drive as code.py. Requires these libraries
# in lib/, from a CircuitPython bundle matching your firmware version:
# - adafruit_is31fl3741
# - adafruit_bus_device
# - adafruit_register

import math
import time

import board
import busio
import digitalio
from adafruit_is31fl3741 import IS31FL3741, MUST_BUFFER

WIDTH = 9
HEIGHT = 34
FPS = 30
SPEED = 1.0  # Animation speed; 0.5 is half speed, 2.0 is double speed.
LED_SCALING = 63  # 0..255; same quarter-brightness limit as led_matrix.py.


def led_index(x, y):
    """Map a matrix coordinate to the LED driver's linear channel index."""
    if y < 30:
        if x < 6:
            return x * 30 + y
        return 180 + (x - 6) * 30 + y
    # The final four rows use the remaining channels on the second page.
    return 180 + 90 + x * 9 + (y - 30)


# Precompute channel addresses so the animation only calculates brightness.
PIXELS = tuple(
    (x, y, led_index(x, y)) for y in range(HEIGHT) for x in range(WIDTH)
)

sdb = digitalio.DigitalInOut(board.SDB)
sdb.direction = digitalio.Direction.OUTPUT
sdb.value = True

i2c = busio.I2C(board.SCL, board.SDA, frequency=400_000)
is31 = IS31FL3741(i2c, address=0x30, allocate=MUST_BUFFER)
is31.set_led_scaling(LED_SCALING)
is31.global_current = 0xFF
is31.enable = True


def plasma_frame(t):
    """Draw the Rust demo's plasma at time t (seconds)."""
    half = WIDTH / 2.0
    cx = half - 0.5 + math.sin(t * 0.5) * (half - 1.5)
    cy = 17.0 + math.cos(t * 0.3) * 12.0
    # These two waves only depend on one coordinate, so reuse them per frame.
    x_wave = [math.sin(x * 0.7 + t * 1.1) for x in range(WIDTH)]
    y_wave = [math.sin(y * 0.23 - t * 1.7) for y in range(HEIGHT)]
    for x, y, channel in PIXELS:
        dx = x - cx
        dy = y - cy
        distance = math.sqrt(dx * dx + dy * dy)
        v = (
            x_wave[x]
            + y_wave[y]
            + math.sin(x * 0.5 + y * 0.15 + t * 0.9)
            + math.sin(distance * 0.35 - t * 2.0)
        )
        brightness = 0.5 + 0.5 * math.sin(v * math.pi / 2.0)
        # Gamma correction: make dim values dimmer for stronger contrast.
        is31[channel] = int(brightness * brightness * 255.0)
    is31.show()


print("LED Matrix plasma running at up to", FPS, "FPS")
start = time.monotonic()
while True:
    frame_start = time.monotonic()
    plasma_frame((frame_start - start) * SPEED)
    # Use elapsed time for motion, even if rendering takes longer than a frame.
    remaining = 1.0 / FPS - (time.monotonic() - frame_start)
    if remaining > 0:
        time.sleep(remaining)
