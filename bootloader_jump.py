# SPDX-FileCopyrightText: 2023 Daniel Schaefer for Framework Computer
# SPDX-License-Identifier: MIT
#
# Jump to the bootloader to flash new UF2 firmware

import microcontroller
microcontroller.on_next_reset(microcontroller.RunMode.UF2)
microcontroller.reset()
