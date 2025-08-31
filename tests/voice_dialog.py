# SPDX-FileCopyrightText: 2025 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3

# load included modules if we aren't installed on the root path
if len(__file__.split("/")[:-1]) > 1:
    import adafruit_pathlib as pathlib
    if (modules_directory := pathlib.Path("/".join(__file__.split("/")[:-1])) / "lib").exists():
        import sys
        sys.path.append(str(modules_directory.absolute()))

import asyncio
import displayio
import sys

import adafruit_imageload

import engine
import graphics

# add background image
bg_bmp, bg_palette = adafruit_imageload.load("bitmaps/bg.bmp")
bg_tg = displayio.TileGrid(bg_bmp, pixel_shader=bg_palette)
graphics.lower_group.append(bg_tg)

engine.VoiceDialog(text="The quick brown fox jumps over the lazy dog. " * 3, title="Lorem Ipsum Dolor Sit Amet").play()

graphics.main_group.hidden = False

async def engine_task() -> None:
    while True:
        engine.update()
        await graphics.refresh()

asyncio.run(engine_task())
