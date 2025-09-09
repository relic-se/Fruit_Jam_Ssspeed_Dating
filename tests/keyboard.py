# SPDX-FileCopyrightText: 2025 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3
import asyncio
import supervisor
import sys

import adafruit_usb_host_mouse

import engine
import graphics

engine.Keyboard().play()

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

async def keyboard_task() -> None:
    while True:
        # handle keyboard input
        while (c := supervisor.runtime.serial_bytes_available) > 0:
            key = sys.stdin.read(c)
            if key == "\n" or key == " ":  # enter or space
                engine.select()
            elif key == "\x08":  # backspace
                # delete character if keyboard is active
                if (event := engine.get_event(engine.Keyboard)) is not None:
                    event.backspace()
            elif len(key) == 1 and key.isalpha():
                # append character if keyboard is active
                if (event := engine.get_event(engine.Keyboard)) is not None:
                    event.append(key)
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
