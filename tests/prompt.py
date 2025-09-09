# SPDX-FileCopyrightText: 2025 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3
import asyncio
import supervisor
import sys

import adafruit_usb_host_mouse

import engine
import graphics

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

async def keyboard_task() -> None:
    while True:
        # handle keyboard input
        while (c := supervisor.runtime.serial_bytes_available) > 0:
            key = sys.stdin.read(c)
            if key == "\x1b[A" or key == "\x1b[D":  # up or left
                engine.up()
            elif key == "\x1b[B" or key == "\x1b[C":  # down or right
                engine.down()
            elif key == "\n" or key == " ":  # enter or space
                engine.select()
        await asyncio.sleep(1/30)

async def engine_task() -> None:
    while True:
        engine.update()
        await graphics.refresh()

async def main():
    await asyncio.gather(
        asyncio.create_task(mouse_task()),
        asyncio.create_task(keyboard_task()),
        asyncio.create_task(engine_task())
    )

asyncio.run(main())
