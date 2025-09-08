# SPDX-FileCopyrightText: 2025 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3
import displayio

import adafruit_bitmapsaver
import adafruit_imageload
import adafruit_pathlib as pathlib

import graphics
import engine
import scene
import sound

SCREENSHOT = "title"

# prepare scene
if SCREENSHOT in {"intro", "results"} or SCREENSHOT.endswith(".json"):

    # add background image
    bg_bmp, bg_palette = adafruit_imageload.load("bitmaps/bg.bmp")
    bg_tg = displayio.TileGrid(bg_bmp, pixel_shader=bg_palette)
    graphics.lower_group.append(bg_tg)

    # add table image
    table_bmp, table_palette = adafruit_imageload.load("bitmaps/table.bmp")
    table_palette.make_transparent(4)
    table_tg = displayio.TileGrid(table_bmp, pixel_shader=table_palette,
                                y=graphics.display.height-table_bmp.height)  # move to bottom of display
    graphics.upper_group.append(table_tg)

    graphics.main_group.hidden = False

# load desired scene
if SCREENSHOT == "title":
    scene.Title().start()

elif SCREENSHOT == "intro":
    scene.Intro().start()
    engine.events[0].complete()  # skip animation

elif SCREENSHOT == "results":
    # generate random results
    import random
    for i in range(len(scene.LEVELS)):
        scene.level_scores[i] = random.randint(-20, 40)

    epilogue = scene.Epilogue()
    epilogue.start()
    sound.stop_music()  # stop music, we don't need it
    engine.events[0].complete()  # skip animation
    epilogue.complete()  # jump to results

elif SCREENSHOT.endswith(".json"):
    scene.DialogueScene(SCREENSHOT).start()
    engine.events[0].complete()  # skip animation

else:
    NotImplementedError("Invalid scene")

# update display
graphics.display.refresh()

# determine screenshot path on sd card, auto-incrementing
i = 0
while (path := pathlib.Path("/sd/screenshot-{:02d}.bmp".format(i))).exists():
    i += 1

print("Saving screenshot to {:s}".format(path.absolute()))
adafruit_bitmapsaver.save_pixels(path.absolute(), graphics.display)
print("Completed saving screenshot")
