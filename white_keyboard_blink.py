import time
import board
import busio
import digitalio
import pwmio

capslock = digitalio.DigitalInOut(board.GP24)
capslock.direction = digitalio.Direction.OUTPUT

backlight = pwmio.PWMOut(board.GP25, frequency=5000, duty_cycle=0)

# Blink capslock LED and backlight
while True:
    capslock.value = True
    backlight.duty_cycle = int(65535 / 2) # 50% brightness
    time.sleep(1)

    capslock.value = False
    backlight.duty_cycle = 0
    time.sleep(1)
