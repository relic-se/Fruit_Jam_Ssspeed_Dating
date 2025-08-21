# SPDX-FileCopyrightText: 2025 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3
import displayio
import supervisor

from adafruit_fruitjam.peripherals import request_display_config
import adafruit_imageload

import config

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

# load the mouse cursor bitmap
cursor_bmp, cursor_palette = adafruit_imageload.load("bitmaps/cursor.bmp")
cursor_palette.make_transparent(0)

# create a TileGrid for the mouse, using its bitmap and pixel_shader
cursor_tg = displayio.TileGrid(
    bitmap=cursor_bmp, pixel_shader=cursor_palette,
    x=display.width//2, y=display.height//2,
)
cursor_tg.hidden = True
root_group.append(cursor_tg)

def refresh() -> None:
    # update display if any changes were made
    display.refresh(target_frames_per_second=config.TARGET_FRAME_RATE)
