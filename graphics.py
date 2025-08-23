# SPDX-FileCopyrightText: 2025 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3
import displayio
import supervisor

from adafruit_fruitjam.peripherals import request_display_config
import asyncio

import config

displayio.release_displays()

# setup display
request_display_config(320, 240)
display = supervisor.runtime.display
display.auto_refresh = False

# create root group
root_group = displayio.Group()
display.root_group = root_group
display.refresh()  # blank out screen

# create group for game elements
main_group = displayio.Group()
main_group.hidden = True
root_group.append(main_group)

# create group for overlay elements
overlay_group = displayio.Group()
root_group.append(overlay_group)

async def refresh() -> None:
    # update display if any changes were made
    display.refresh()
    await asyncio.sleep(1/config.TARGET_FRAME_RATE)
