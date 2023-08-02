import board
import busio
import digitalio

# Enable LED Matrix Controller
sdb = digitalio.DigitalInOut(board.GP29)
sdb.direction = digitalio.Direction.OUTPUT
sdb.value = True

from adafruit_is31fl3731 import IS31FL3731
i2c = busio.I2C(board.SCL, board.SDA)
i2c.try_lock()
print('\n i2c scan: ' + str(i2c.scan()))
i2c.unlock()

# TODO: Doesn't seem to work yet
display = IS31FL3731(i2c, address=0x20)
display.fill(250)
