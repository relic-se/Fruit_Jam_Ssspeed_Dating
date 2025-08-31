# SPDX-FileCopyrightText: 2025 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3
import displayio
import supervisor

from adafruit_fruitjam.peripherals import request_display_config
import adafruit_imageload
import asyncio

import config

displayio.release_displays()

def copy_palette(palette:displayio.Palette) -> displayio.Palette:
    clone = displayio.Palette(len(palette))
    for i, color in enumerate(palette):
        # Add color to new_palette
        clone[i] = color
        # Set new_palette color index transparency
        if palette.is_transparent(i):
            clone.make_transparent(i)
    return clone

# setup display
request_display_config(320, 240)
display = supervisor.runtime.display
display.auto_refresh = False

# create root group
root_group = displayio.Group()
display.root_group = root_group
display.refresh()  # blank out screen

# create groups for game elements
main_group = displayio.Group()
main_group.hidden = True
root_group.append(main_group)

lower_group = displayio.Group()
main_group.append(lower_group)

upper_group = displayio.Group()
main_group.append(upper_group)

# create group for overlay elements
overlay_group = displayio.Group()
root_group.append(overlay_group)

async def refresh() -> None:
    # update display if any changes were made
    display.refresh()
    await asyncio.sleep(1/config.TARGET_FRAME_RATE)

# load the fade bitmap
fade_bmp, fade_palette = adafruit_imageload.load("bitmaps/fade.bmp")
fade_palette.make_transparent(1)
FADE_TILE_SIZE = fade_bmp.height
FADE_TILES = fade_bmp.width // FADE_TILE_SIZE

# load window image
window_bmp, window_palette = adafruit_imageload.load("bitmaps/window.bmp")
window_palette.make_transparent(1)
WINDOW_TILE_SIZE = 8

# mouse cursor
cursor = None
def set_cursor(tilegrid:displayio.TileGrid) -> None:
    global cursor
    if cursor is not None:
        reset_cursor()
    cursor = tilegrid
    cursor.x = display.width // 2
    cursor.y = display.height // 2
    root_group.append(cursor)

def reset_cursor():
    global cursor
    root_group.remove(cursor)
    cursor = None

def get_cursor_pos() -> tuple:
    return (cursor.x, cursor.y, 0)
