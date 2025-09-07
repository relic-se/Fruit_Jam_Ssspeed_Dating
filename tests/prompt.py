# SPDX-FileCopyrightText: 2025 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3
import asyncio
import displayio

import adafruit_imageload
import adafruit_usb_host_mouse

import engine
import graphics

# add background image (to test fade)
bg_bmp, bg_palette = adafruit_imageload.load("bitmaps/bg.bmp")
bg_tg = displayio.TileGrid(bg_bmp, pixel_shader=bg_palette)
graphics.lower_group.append(bg_tg)

def prompt(selected:int=None) -> None:
    if selected is not None:
        print(selected)
    engine.Prompt(
        text="Hello, World!",
        options=("Yes", "No", "Cancel"),
        on_complete=prompt,
    ).play()
prompt()

graphics.main_group.hidden = False

async def mouse_task() -> None:
    while True:
        if (mouse := adafruit_usb_host_mouse.find_and_init_boot_mouse("bitmaps/cursor.bmp")) is not None:
            graphics.set_cursor(mouse.tilegrid)
            timeouts = 0
            while timeouts < 9999:
                pressed_btns = mouse.update()
                if pressed_btns is None:
                    timeouts += 1
                else:
                    timeouts = 0
                    if "left" in pressed_btns:
                        engine.mouseclick()
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
