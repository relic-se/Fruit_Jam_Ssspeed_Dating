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

# generate random level scores
import random
for i in range(len(scene.LEVELS)):
    scene.level_scores[i] = random.randint(-20, 40)

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

def take_screenshot() -> None:
    # stop background music, we don't need it
    sound.stop_music()

    # update display
    graphics.display.refresh()

    # determine screenshot path on sd card, auto-incrementing
    i = 0
    while (path := pathlib.Path("/sd/screenshot-{:02d}.bmp".format(i))).exists():
        i += 1

    print("Saving screenshot to {:s}".format(path.absolute()))
    adafruit_bitmapsaver.save_pixels(path.absolute(), graphics.display)
    print("Completed saving screenshot")

    # stop all events
    while engine.events:
        engine.events[-1].stop()
    if scene.current_scene is not None:
        scene.current_scene.stop()

# title
scene.Title().start()
take_screenshot()

# intro
graphics.main_group.hidden = False
scene.Intro().start()
engine.events[0].complete()  # skip animation
take_screenshot()

# results
epilogue = scene.Epilogue()
epilogue.start()
engine.events[0].complete()  # skip animation
epilogue.complete()  # jump to results
take_screenshot()

# levels
for level in scene.LEVELS:
    scene.DialogueScene(level).start()
    engine.events[0].complete()  # skip animation
    take_screenshot()
