# SPDX-FileCopyrightText: 2025 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3
import asyncio
import displayio

import adafruit_imageload
import adafruit_usb_host_mouse

import engine
import graphics
import scene

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

scene.DialogueScene("02-max.json").start()

graphics.main_group.hidden = False

async def mouse_task() -> None:
    while True:
        if (mouse := adafruit_usb_host_mouse.find_and_init_boot_mouse("bitmaps/cursor.bmp")) is not None:
            graphics.set_cursor(mouse.tilegrid)
            timeouts = 0
            previous_pressed_btns = []
            while timeouts < 9999:
                pressed_btns = mouse.update()
                if pressed_btns is None:
                    timeouts += 1
                else:
                    timeouts = 0
                    if "left" in pressed_btns and (previous_pressed_btns is None or "left" not in previous_pressed_btns):
                        engine.mouseclick()
                previous_pressed_btns = pressed_btns
                await asyncio.sleep(1/30)
            graphics.reset_cursor()
        await asyncio.sleep(1)

async def engine_task() -> None:
    while True:
        engine.update()
        await graphics.refresh()

async def main():
    await asyncio.gather(
        asyncio.create_task(mouse_task()),
        asyncio.create_task(engine_task())
    )

asyncio.run(main())
