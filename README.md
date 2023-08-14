# CircuitPython Scripts for Framework 16 Input Modules

This is not the official firmware for the Framework 16 Input Modules.
But we want to make it as easy as possible to hack on the modules. As an alternative firmware for playing around, you can use circuitpython to easily write some scripts and run them in the firmware.

Going back to official firmware is as easy as triggering the bootloader mode and copying the official UF2 files on the RP2 drive.

## Preparation

Not supported in upstream CircuitPython yet.
Clone from the [pull request](https://github.com/adafruit/circuitpython/pull/8233).

Follow the official [build guide](https://learn.adafruit.com/building-circuitpython).
Once your environment is set up you can compile with:

```sh
cd ports/raspberrypi
make BOARD=fwk_keyboard

# Use firmware at build-fwk_keyboard/firmware.uf2
```

Flash the firmware once and you're good to go.

To go back to Framework official firmware

## Support

- Any Module
  - [x] Jump to bootloader: `bootloader_jump.py`
  - [x] Read sleep pin
- Any keyboard
  - [ ] Scan keys
- White Backlight Keyboard
  - [x] Control Backlight
  - [x] Control Capslock LED
  - [x] Example: `white_keyboard_blink.py`
- RGB Keyboard
  - [ ] Control RGB Backlight
  - [ ] Example
- RGB Macropad
  - [x] Control RGB Backlight: `macropad_backlight.py`
  - [ ] Scan keys
- LED Matrix
  - [x] Control LED Matrix
  - [x] Example WIP: `led_matrix.py`
