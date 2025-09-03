# SPDX-FileCopyrightText: 2025 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3

# load included modules if we aren't installed on the root path
if len(__file__.split("/")[:-1]) > 1:
    import adafruit_pathlib as pathlib
    if (modules_directory := pathlib.Path("/".join(__file__.split("/")[:-1])) / "lib").exists():
        import sys
        sys.path.append(str(modules_directory.absolute()))

import displayio
from micropython import const
import sys
import supervisor
from terminalio import FONT

import adafruit_imageload
import adafruit_usb_host_mouse
import asyncio
import relic_usb_host_gamepad

import config
import engine
import graphics
import hardware
import scene
import sound

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

# start title screen
scene.Title().start()

ACTION_SELECT = const(0)
ACTION_UP     = const(1)
ACTION_DOWN   = const(2)
ACTION_PAUSE  = const(3)
ACTION_QUIT   = const(4)

def do_action(action:int) -> None:
    global started
    if action == ACTION_SELECT:
        sound.play_sfx(sound.SFX_CLICK)
        if engine.current_event is not None:
            engine.current_event.select()
    elif action == ACTION_QUIT:
        supervisor.reload()

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
                        do_action(ACTION_SELECT)
                previous_pressed_btns = pressed_btns
                await asyncio.sleep(1/config.TARGET_FRAME_RATE)
            graphics.reset_cursor()
        await asyncio.sleep(1)

async def gamepad_task() -> None:
    gamepad = relic_usb_host_gamepad.Gamepad()
    while True:
        if gamepad.update():
            if gamepad.buttons.UP.pressed or gamepad.buttons.JOYSTICK_UP.pressed:
                do_action(ACTION_UP)
            elif gamepad.buttons.DOWN.pressed or gamepad.buttons.JOYSTICK_DOWN.pressed:
                do_action(ACTION_DOWN)
            elif gamepad.buttons.A.pressed:
                do_action(ACTION_SELECT)
            elif gamepad.buttons.START.pressed:
                do_action(ACTION_PAUSE)
            elif gamepad.buttons.HOME.pressed:
                do_action(ACTION_QUIT)
        elif not gamepad.connected:
            await asyncio.sleep(1)
        else:
            await asyncio.sleep(1/config.TARGET_FRAME_RATE)

async def keyboard_task() -> None:
    while True:
        # handle keyboard input
        while (c := supervisor.runtime.serial_bytes_available) > 0:
            key = sys.stdin.read(c)
            if key == "\x1b[A":  # up key
                do_action(ACTION_UP)
            elif key == "\x1b[B":  # down key
                do_action(ACTION_DOWN)
            elif key == "\n" or key.lower() == "z":  # enter
                do_action(ACTION_SELECT)
            elif key == "\x1b":  # escape
                do_action(ACTION_PAUSE)
            elif key.lower() == "q":
                do_action(ACTION_QUIT)
        await asyncio.sleep(1/config.TARGET_FRAME_RATE)

if hardware.buttons is not None:
    async def buttons_task() -> None:
        while True:
            if (event := hardware.buttons.events.get()):
                if event.pressed:
                    if event.key_number == 0:
                        do_action(ACTION_DOWN)
                    elif event.key_number == 1:
                        do_action(ACTION_SELECT)
                    elif event.key_number == 2:
                        do_action(ACTION_UP)
            await asyncio.sleep(1/config.TARGET_FRAME_RATE)

async def engine_task() -> None:
    while True:
        engine.update()
        await graphics.refresh()

async def main():
    tasks = [
        asyncio.create_task(mouse_task()),
        asyncio.create_task(gamepad_task()),
        asyncio.create_task(keyboard_task()),
        asyncio.create_task(engine_task()),
    ]
    if hardware.buttons is not None:
        tasks.append(asyncio.create_task(buttons_task()))
    await asyncio.gather(*tasks)

asyncio.run(main())
