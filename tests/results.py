# SPDX-FileCopyrightText: 2025 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3
import asyncio
import displayio
import random

import adafruit_imageload

import engine
import graphics
import scene

# add background image
bg_bmp, bg_palette = adafruit_imageload.load("bitmaps/bg.bmp")
bg_tg = displayio.TileGrid(bg_bmp, pixel_shader=bg_palette)
graphics.lower_group.append(bg_tg)

# simulate level scores
for i in range(len(scene.level_scores)):
    scene.level_scores[i] = random.randint(-20, 30)

engine.Results().play()

graphics.main_group.hidden = False

async def engine_task() -> None:
    while True:
        engine.update()
        await graphics.refresh()

asyncio.run(engine_task())
