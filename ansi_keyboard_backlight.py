# SPDX-FileCopyrightText: 2023 Daniel Schaefer for Framework Computer
# SPDX-License-Identifier: MIT

import time
import board
import busio
import digitalio
from framework_is31fl3743 import IS31FL3743

# Enable LED controller via SDB pin
sdb = digitalio.DigitalInOut(board.GP29)
sdb.direction = digitalio.Direction.OUTPUT
sdb.value = True

i2c = busio.I2C(board.SCL, board.SDA)  # Or board.I2C()

# TODO: If I don't scan the bus, creating IS31FL3743 can't find the device. Why...?
i2c.try_lock()
i2c.scan()
i2c.unlock()

is31_controllers = [IS31FL3743(i2c, address=0x20), IS31FL3743(i2c, address=0x23)]
for is31 in is31_controllers:
    is31.set_led_scaling(int(0xFF / 1))  # Full brightness
    is31.global_current = 0xFF  # set current to max
    is31.enable = True
# SLEEP# pin. Low if the host is sleeping
sleep_pin = digitalio.DigitalInOut(board.GP0)
sleep_pin.direction = digitalio.Direction.INPUT

# Keep in the script to keep the LED controller on
color = 0
while True:
    # Change to a different color every iteration
    # 0 red
    # 1 blue
    # 2 green
    # 3 white
    # 4 black/off
    color = (color + 1) % 4

    for is31 in is31_controllers:
        is31.enable = sleep_pin.value

        for i in range(18 * 11):
            is31[i] = 0xFF if color != 4 and color in (3, i % 3) else 0x00
    time.sleep(1)
