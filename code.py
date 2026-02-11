# SPDX-FileCopyrightText: 2025 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3

# load included modules if we aren't installed on the root path
if len(__file__.split("/")[:-1]) > 1:
    lib_path = "/".join(__file__.split("/")[:-1]) + "/lib"
    try:
        import os
        os.stat(lib_path)
    except:
        pass
    else:
        import sys
        sys.path.append(lib_path)

import asyncio
from relic_usb_host_gamepad import (
    BUTTON_UP, BUTTON_JOYSTICK_UP,
    BUTTON_DOWN, BUTTON_JOYSTICK_DOWN,
    BUTTON_LEFT, BUTTON_JOYSTICK_LEFT,
    BUTTON_RIGHT, BUTTON_JOYSTICK_RIGHT,
    BUTTON_A,
    BUTTON_START, BUTTON_SELECT, BUTTON_HOME,
)

import engine
import graphics
import hardware
import scene

try:
    import supervisor
except ImportError:
    from relic_usb_host_gamepad.pygame import Gamepad
    import pygame
    import adafruit_imageload
    from displayio import Bitmap, Palette, TileGrid
    BLINKA = True
else:
    import sys
    from relic_usb_host_gamepad import Gamepad
    import adafruit_usb_host_mouse
    BLINKA = False

# start title screen
scene.Title().start()

async def mouse_task() -> None:
    if BLINKA:
        mouse_bitmap, mouse_palette = adafruit_imageload.load(
            "bitmaps/cursor.bmp",
            bitmap=Bitmap, palette=Palette
        )
        mouse_palette.make_transparent(0)
        mouse_tg = TileGrid(
            bitmap=mouse_bitmap, pixel_shader=mouse_palette,
            x=graphics.display.width//2, y=graphics.display.height//2,
        )
        graphics.set_cursor(mouse_tg)

        while True:
            for event in pygame.event.get(eventtype=(pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN)):
                if event.type == pygame.MOUSEMOTION:
                    mouse_tg.x, mouse_tg.y = event.pos
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    engine.mouseclick()
            await asyncio.sleep(1/30)

    else:
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

gamepad = Gamepad()
async def gamepad_task() -> None:
    global gamepad
    while True:
        if gamepad.update():
            for event in gamepad.events:
                if event.pressed:
                    if event.key_number in (BUTTON_UP, BUTTON_JOYSTICK_UP):
                        engine.up()
                    elif event.key_number in (BUTTON_DOWN, BUTTON_JOYSTICK_DOWN):
                        engine.down()
                    elif event.key_number in (BUTTON_LEFT, BUTTON_JOYSTICK_LEFT):
                        engine.left()
                    elif event.key_number in (BUTTON_RIGHT, BUTTON_JOYSTICK_RIGHT):
                        engine.right()
                    elif event.key_number == BUTTON_A:
                        engine.select()
                    elif event.key_number in (BUTTON_START, BUTTON_SELECT, BUTTON_HOME):
                        # activate exit prompt
                        if (event := engine.get_event(engine.Exit)) is not None:
                            event.complete()
        await asyncio.sleep(1/30 if gamepad.connected else 1)

async def keyboard_task() -> None:

    def handle_key(key: str) -> None:
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
    
    while True:
        # handle keyboard input
        if BLINKA:
            for event in pygame.event.get(eventtype=(pygame.KEYDOWN,)):
                handle_key(event.unicode.upper())
        else:
            while (available := supervisor.runtime.serial_bytes_available) > 0:
                buffer = sys.stdin.read(available)
                while buffer:
                    key = buffer[0]
                    buffer = buffer[1:]
                    if key == "\x1b" and buffer and buffer[0] == "[" and len(buffer) >= 2:
                        key += buffer[:2]
                        buffer = buffer[2:]
                        if buffer and buffer[0] == "~":
                            key += buffer[0]
                            buffer = buffer[1:]
                    handle_key(key.upper())
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
        if BLINKA and graphics.display.check_quit():
            exit()
        engine.update()
        await graphics.refresh()

async def main():
    tasks = [
        asyncio.create_task(mouse_task()),
        asyncio.create_task(gamepad_task()),
        asyncio.create_task(keyboard_task()),
        asyncio.create_task(engine_task()),
    ]
    if not BLINKA:
        tasks.append(asyncio.create_task(buttons_task()))
    await asyncio.gather(*tasks)

try:
    asyncio.run(main())
except KeyboardInterrupt:
    gamepad.disconnect()
    if not BLINKA:
        hardware.peripherals.deinit()
    raise KeyboardInterrupt
