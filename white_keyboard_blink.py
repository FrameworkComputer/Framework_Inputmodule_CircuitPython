import time
import board
import digitalio
import pwmio

capslock = digitalio.DigitalInOut(board.GP24)
capslock.direction = digitalio.Direction.OUTPUT

# SLEEP# pin. Low if the host is sleeping
sleep_pin = digitalio.DigitalInOut(board.GP0)
sleep_pin.direction = digitalio.Direction.INPUT

backlight = pwmio.PWMOut(board.GP25, frequency=5000, duty_cycle=0)

# Blink capslock LED and backlight
while True:
    sleeping = not sleep_pin.value
    if sleeping:
        # If the host is asleep, stop blinking
        time.sleep(0.1)
        continue
    capslock.value = True
    backlight.duty_cycle = int(65535 / 2)  # 50% brightness
    time.sleep(1)

    capslock.value = False
    backlight.duty_cycle = 0
    time.sleep(1)
