"""Make a capture replay faster without touching the original file."""

# atbswp: Record mouse and keyboard actions and reproduce them identically at will
#
# Copyright (C) 2019 Paul Mairo <github@rmpr.xyz>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import re

MAX_SPEED = float("inf")  # no recorded wait at all, only the minimum wait
SPEEDS = (1, 2, 3, 5, 10, 20, 50, MAX_SPEED)
DEFAULT_MIN_WAIT = 0.05
PAUSE_LINE = "pyautogui.PAUSE = 0"

SLEEP_RE = re.compile(r"^time\.sleep\(\s*([^)]*?)\s*\)$")
PAUSE_RE = re.compile(r"^pyautogui\.PAUSE\s*=")
MOVE_PREFIX = "pyautogui.moveTo("


def speed_label(speed):
    """Return '3x', '2.5x' or 'max'."""
    return "max" if speed == MAX_SPEED else f"{speed:g}x"


def transform(lines, speed=1.0, skip_moves=False, min_wait=DEFAULT_MIN_WAIT):
    """Return the lines of a faster version of the capture `lines`.

    Keyword arguments:
    speed -- every recorded time.sleep is divided by this factor
    skip_moves -- only keep the last mouse position before each click/key
    min_wait -- never wait less than this (seconds) before a click/key/scroll

    The pyautogui pause after each call is set to 0, `min_wait` replaces it.
    """
    if speed <= 0:
        raise ValueError("speed must be greater than 0")
    if min_wait < 0:
        raise ValueError("min_wait must not be negative")

    out = []
    pending = 0.0      # recorded delay not written yet
    last_move = None   # last skipped moveTo
    pause_written = False

    def write_wait(floor):
        nonlocal pending
        wait = max(pending / speed, floor)
        if wait > 0:
            out.append(f"time.sleep({wait})")
        pending = 0.0

    for raw in lines:
        line = raw.strip()
        sleep = SLEEP_RE.match(line)
        if sleep:
            pending += float(sleep.group(1))
        elif PAUSE_RE.match(line):
            continue
        elif line.startswith(MOVE_PREFIX):
            if skip_moves:
                last_move = line
            else:
                write_wait(0.0)
                out.append(line)
        elif line.startswith("pyautogui.") and "(" in line:
            # Click, scroll or key: hover first, then wait, then act
            if last_move:
                out.append(last_move)
                last_move = None
            write_wait(min_wait)
            out.append(line)
        else:
            out.append(line)
            if line == "import pyautogui" and not pause_written:
                out.append(PAUSE_LINE)
                pause_written = True

    if last_move:
        out.append(last_move)
    write_wait(0.0)
    if not pause_written:
        out[:0] = ["import pyautogui", "import time", PAUSE_LINE]
    return out
