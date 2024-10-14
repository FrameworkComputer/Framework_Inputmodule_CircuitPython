# SPDX-FileCopyrightText: 2023-2024 Daniel Schaefer for Framework Computer
# SPDX-License-Identifier: MIT
#
# Show zigzag pattern on LED matrix. Turn off if SLEEP# pin is low.
#
# Dependencies:
# On the CIRCUITPY drive
# - Save this file as code.py
# - Make sure there's a lib folder and download:
#   - adafruit_bitmap_font
#   - adafruit_bus_device
#   - adafruit_display_text
#   - adafruit_is31fl3741
#   - adafruit_led_animation
#   - adafruit_register
#   - adafruit_framebuf.mpy
# All contained in the project bundle at:
#   https://learn.adafruit.com/adafruit-is31fl3741/python-circuitpython#basic-example-code-3102692
# Or (more stable URL) from:
#   https://github.com/adafruit/Adafruit_CircuitPython_Bundle/releases
#   adafruit-circuitpython-bundle-8.x-mpy*.zip

import time
import board
from adafruit_is31fl3741 import IS31FL3741
import digitalio
import busio

from ledmatrix_mapping import mapping

WIDTH = 9
HEIGHT = 34

# Enable LED Matrix via SDB pin
sdb = digitalio.DigitalInOut(board.GP29)
sdb.direction = digitalio.Direction.OUTPUT
sdb.value = True

i2c = busio.I2C(board.SCL, board.SDA)  # Or board.I2C()
is31 = IS31FL3741(i2c, address=0x30)

is31.set_led_scaling(int(0xFF / 4))  # Quarter brightness
is31.global_current = 0xFF  # set current to max
is31.enable = True

for i in range(WIDTH * HEIGHT):
    x = i % WIDTH
    y = i % HEIGHT
    (addr, page) = mapping[x + y * WIDTH]
    idx = addr + 180 * page
    # Zigzag pattern to make sure we can properly address every coordinate
    is31[idx] = (
        0xFF
        if (y % (WIDTH * 2) < WIDTH and x == y % WIDTH)
        or (y % 18 >= WIDTH and x == WIDTH - y % WIDTH)
        else 0x00
    )
# Keep in the script to keep the LED controller on
while True:
    time.sleep(0.01)
