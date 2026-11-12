# SPDX-FileCopyrightText: Daniel Schaefer 2023 for Framework Computer
# SPDX-License-Identifier: MIT
#
# Key matrix scanning shared by the Framework Laptop 16 keyboards, numpad and
# macropad. Copy this file to the CIRCUITPY drive next to code.py (or into lib/).
#
# The matrix is read through an analog mux: each column (KSO) is driven low in
# turn, and each row (KSI) is read with the ADC. A pressed key pulls its row low.
#
# Usage:
#   scanner = KeyScanner(matrix)  # matrix[row][col], None where there's no key
#   for (row, col), pressed in scanner.scan():
#       ...

import time
import board
import digitalio
import analogio

# A single pressed key reads ~0.0-0.3V. Idle keys settle at ~1.9-3.3V.
# For a scan after a key in a row is pressed or released, the other keys in that
# row sag to ~0.3-1.5V, so keep the threshold low.
ADC_THRESHOLD = 0.5
# When exactly two keys in the same row (KSI) are held, e.g. Fn+F2, both read
# ~1.6-1.7V and none reads below ADC_THRESHOLD, while the rest of the row stays
# idle. In that case both count as pressed. More than two keys below this
# threshold is the whole row sagging, not key presses.
# Must stay below the idle voltage (~1.9V).
# Three or more held keys in one row are not supported.
MULTI_THRESHOLD = 1.8
# The rows read low right after the pins are configured until they charge up.
# Ignore scans during this time to avoid phantom key presses.
STARTUP_SETTLE_S = 1.0
# A key has to read the same for this many consecutive scans to change state.
# Presses reading below ADC_THRESHOLD, with the rest of the row idle, are taken
# after one scan for lower latency.
DEBOUNCE_SCANS = 2

_KSO_PINS = [
    # KSO0 - KSO7 for Keyboards, Numpad and Macropad
    "KSO0",
    "KSO1",
    "KSO2",
    "KSO3",
    "KSO4",
    "KSO5",
    "KSO6",
    "KSO7",
    # KSO8 - KSO15 for Keyboards only
    "KSO8",
    "KSO9",
    "KSO10",
    "KSO11",
    "KSO12",
    "KSO13",
    "KSO14",
    "KSO15",
]


def _output(pin, value=False):
    io = digitalio.DigitalInOut(pin)
    io.direction = digitalio.Direction.OUTPUT
    io.value = value
    return io


class KeyScanner:
    def __init__(self, matrix, debug_low_v=None, debug=False):
        """
        matrix: list of rows (KSI), each a list of columns (KSO). Any non-None
            entry is a key. Only used to know which positions have a key and
            for debug output.
        debug_low_v: Print every key reading below this voltage whenever those
            readings change, and the scan rate every 10s. Useful for tuning the
            thresholds. None to disable.
        debug: Print every single ADC reading.
        """
        self.matrix = matrix
        self.rows = len(matrix)
        self.cols = len(matrix[0])
        self.debug_low_v = debug_low_v
        self.debug = debug

        # Low to enable the mux
        self._mux_enable = _output(board.MUX_ENABLE, False)
        self._mux = [_output(board.MUX_A), _output(board.MUX_B), _output(board.MUX_C)]
        self._kso = [_output(getattr(board, name), True) for name in _KSO_PINS[: self.cols]]
        self._adc = analogio.AnalogIn(board.ANALOG_IN)
        # Signal boot done
        self._boot_done = _output(board.BOOT_DONE, False)

        # Positions to read, per column
        self._positions = [
            [row for row in range(self.rows) if matrix[row][col] is not None]
            for col in range(self.cols)
        ]

        # Debounced state
        self.pressed = set()
        # How many consecutive scans each position has disagreed with pressed
        self._pending = {}

        self._debug_lows = {}
        self._scan_count = 0
        self._scan_rate_start = time.monotonic()

        # Keep scanning (and discarding results) until the row lines have charged up
        settle_end = time.monotonic() + STARTUP_SETTLE_S
        while time.monotonic() < settle_end:
            self._read_matrix()

    def _select_row(self, row):
        # Mux inputs are not in order:
        # X0 - KSI1, X1 - KSI2, X2 - KSI0, X3-X7 - KSI3-KSI7
        if row == 0:
            index = 2
        elif row == 1:
            index = 0
        elif row == 2:
            index = 1
        else:
            index = row

        self._mux[0].value = index & 0x01
        self._mux[1].value = index & 0x02
        self._mux[2].value = index & 0x04

    def _read_matrix(self):
        """
        Read the raw matrix.
        Returns (pressed, fast): All positions that read as pressed, and the
        ones that are clear enough to be taken without debouncing.
        """
        lows = {}
        # Per row: columns reading below ADC_THRESHOLD and below MULTI_THRESHOLD
        strong = [[] for _ in range(self.rows)]
        weak = [[] for _ in range(self.rows)]

        for col in range(self.cols):
            self._kso[col].value = False

            for row in self._positions[col]:
                self._select_row(row)

                voltage = (self._adc.value * 3.3) / 65536
                if self.debug:
                    print(f"KSO{col}:KSI{row}: {voltage:.2f}V")
                if self.debug_low_v is not None and voltage < self.debug_low_v:
                    lows[self.matrix[row][col]] = round(voltage, 1)

                if voltage < ADC_THRESHOLD:
                    strong[row].append(col)
                elif voltage < MULTI_THRESHOLD:
                    weak[row].append(col)

            self._kso[col].value = True

        pressed = set()
        fast = set()
        for row in range(self.rows):
            if strong[row]:
                # A held key reads ~0V. Ignore its neighbors that dip a bit.
                for col in strong[row]:
                    pressed.add((row, col))
                    # When a key is released, its whole row dips for a scan and
                    # neighbors can briefly read below ADC_THRESHOLD, with others
                    # in between. Only take the fast path if the rest of the row
                    # reads idle.
                    if not weak[row]:
                        fast.add((row, col))
            elif len(weak[row]) == 2:
                # Two held keys in the same row both rise to ~1.6-1.7V
                for col in weak[row]:
                    pressed.add((row, col))

        if self.debug_low_v is not None and lows != self._debug_lows:
            self._debug_lows = lows
            print(" ".join(f"{k}={v}" for k, v in sorted(lows.items())) or "-")
        return (pressed, fast)

    def scan(self):
        """
        Scan the matrix once and return the debounced changes as a list of
        ((row, col), pressed) tuples.
        """
        (raw, fast) = self._read_matrix()

        if self.debug_low_v is not None:
            self._scan_count += 1
            now = time.monotonic()
            if now - self._scan_rate_start >= 10:
                print(f"{self._scan_count / (now - self._scan_rate_start):.0f} scans/s")
                self._scan_count = 0
                self._scan_rate_start = now

        # Debounce: every position that differs from the debounced state must
        # stay that way for DEBOUNCE_SCANS scans (one scan for fast presses)
        events = []
        changed = raw ^ self.pressed
        for pos in list(self._pending):
            if pos not in changed:
                del self._pending[pos]
        for pos in changed:
            self._pending[pos] = self._pending.get(pos, 0) + 1
            needed = 1 if pos in fast else DEBOUNCE_SCANS
            if self._pending[pos] < needed:
                continue
            del self._pending[pos]
            is_pressed = pos in raw
            if is_pressed:
                self.pressed.add(pos)
            else:
                self.pressed.discard(pos)
            if self.debug:
                (row, col) = pos
                state = "Pressed" if is_pressed else "Released"
                print(f"{state} {self.matrix[row][col]} (KSO{col}, KSI{row})")
            events.append((pos, is_pressed))
        return events

    def reset(self):
        """
        Forget all pressed keys, e.g. while the host is asleep.
        Doesn't generate release events.
        """
        self.pressed.clear()
        self._pending.clear()
