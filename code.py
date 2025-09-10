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
#import relic_usb_host_gamepad

import engine
import graphics
import hardware
import scene

# start title screen
scene.Title().start()

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

"""
async def gamepad_task() -> None:
    gamepad = relic_usb_host_gamepad.Gamepad()
    while True:
        if gamepad.update():
            if gamepad.buttons.UP.pressed or gamepad.buttons.JOYSTICK_UP.pressed:
                engine.up()
            elif gamepad.buttons.DOWN.pressed or gamepad.buttons.JOYSTICK_DOWN.pressed:
                engine.down()
            elif gamepad.buttons.LEFT.pressed or gamepad.buttons.JOYSTICK_LEFT.pressed:
                engine.left()
            elif gamepad.buttons.RIGHT.pressed or gamepad.buttons.JOYSTICK_RIGHT.pressed:
                engine.right()
            elif gamepad.buttons.A.pressed:
                engine.select()
            elif gamepad.buttons.START.pressed or gamepad.buttons.SELECT.pressed or gamepad.buttons.HOME.pressed:
                # activate exit prompt
                if (event := engine.get_event(engine.Exit)) is not None:
                    event.complete()
        elif not gamepad.connected:
            await asyncio.sleep(1)
        else:
            await asyncio.sleep(1/30)
"""

async def keyboard_task() -> None:
    while True:
        # handle keyboard input
        while (c := supervisor.runtime.serial_bytes_available) > 0:
            key = sys.stdin.read(c)
            if (event := engine.get_event(engine.Keyboard)) is not None:
                if key == "\n" or key == " ":  # enter or space
                    event.complete()
                elif key == "\x08":  # backspace
                    event.backspace()
                elif len(key) == 1 and key.isalpha():
                    event.append(key)
            else:
                if key == "\x1b[A" or key == "\x1b[D":  # up
                    engine.up()
                elif key == "\x1b[B" or key == "\x1b[C":  # down
                    engine.down()
                elif key == "\x1b[D":  # left
                    engine.left()
                elif key == "\x1b[C":  # right
                    engine.right()
                elif key == "\n" or key == " ":  # enter or space
                    engine.select()
            if key == "\x1b" and (event := engine.get_event(engine.Exit)) is not None:  # escape
                event.complete()
        await asyncio.sleep(1/30)

async def buttons_task() -> None:
    last_state = 0
    while True:
        state = 0
        for i, button in enumerate((hardware.peripherals.button1, hardware.peripherals.button2, hardware.peripherals.button3)):
            state |= int(button) << i
        diff = last_state ^ state

        if (event := engine.get_event(engine.Keyboard)) is not None:
            for i, action in enumerate((engine.select, event.right, event.left)):
                if diff & (1 << i) and state & (1 << i):
                    if i == 0:
                        action()
                    else:
                        action(wrap=False)
        else:
            for i, action in enumerate((engine.select, engine.down, engine.up)):
                if diff & (1 << i) and state & (1 << i):
                    action()
        last_state = state
        await asyncio.sleep(0.1)

async def engine_task() -> None:
    while True:
        engine.update()
        await graphics.refresh()

async def main():
    await asyncio.gather(
        asyncio.create_task(mouse_task()),
        #asyncio.create_task(gamepad_task()),
        asyncio.create_task(keyboard_task()),
        asyncio.create_task(engine_task()),
        asyncio.create_task(buttons_task()),
    )

asyncio.run(main())
