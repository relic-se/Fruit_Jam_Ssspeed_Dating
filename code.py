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
import fontio
import math
from micropython import const
import sys
import supervisor
from terminalio import FONT

from adafruit_display_text.label import Label
from adafruit_display_text.text_box import TextBox
import adafruit_imageload
import adafruit_usb_host_mouse
import asyncio
from font_knewave_outline_webfont_18 import FONT as FONT_TITLE
import relic_usb_host_gamepad

import config
import engine
import hardware
import sound
import graphics

# add background image
bg_bmp, bg_palette = adafruit_imageload.load("bitmaps/bg.bmp")
bg_tg = displayio.TileGrid(bg_bmp, pixel_shader=bg_palette)
graphics.main_group.append(bg_tg)

# add blinka
snake_bmp, snake_palette = adafruit_imageload.load("bitmaps/ozzie.bmp")
snake_palette.make_transparent(5)
snake_tg = displayio.TileGrid(snake_bmp, pixel_shader=snake_palette,
                              x=graphics.display.width, y=25)
graphics.main_group.append(snake_tg)

# add table image
table_bmp, table_palette = adafruit_imageload.load("bitmaps/table.bmp")
table_palette.make_transparent(3)
table_tg = displayio.TileGrid(table_bmp, pixel_shader=table_palette,
                              y=graphics.display.height-table_bmp.height)  # move to bottom of display
graphics.main_group.append(table_tg)

# load window image
window_bmp, window_palette = adafruit_imageload.load("bitmaps/window.bmp")
window_palette.make_transparent(1)
WINDOW_TILE_SIZE = 8

class TextWindow(displayio.Group):

    def __init__(self, width:int, height:int, text:str="", font:fontio.FontProtocol=FONT, **kwargs):
        super().__init__(**kwargs)
        width = math.ceil(width / WINDOW_TILE_SIZE)
        height = math.ceil(height / WINDOW_TILE_SIZE)
        if width < 3 or height < 3:
            raise ValueError("Width and/or height are too small!")
        
        # setup window background grid
        self._tg = displayio.TileGrid(
            bitmap=window_bmp, pixel_shader=window_palette,
            width=width, height=height,
            tile_width=WINDOW_TILE_SIZE, tile_height=WINDOW_TILE_SIZE, default_tile=4,
        )
        self.append(self._tg)

        # set corners
        self._tg[0, 0] = 0
        self._tg[self._tg.width-1, 0] = 2
        self._tg[0, self._tg.height-1] = 6
        self._tg[self._tg.width-1, self._tg.height-1] = 8

        # set borders
        for x in range(1, self._tg.width-1):
            self._tg[x, 0] = 1
            self._tg[x, self._tg.height-1] = 7
        for y in range(1, self._tg.height-1):
            self._tg[0, y] = 3
            self._tg[self._tg.width-1, y] = 5

        # setup textbox
        try:
            bb_width, bb_height, bb_x_offset, bb_y_offset = font.get_bounding_box()
        except ValueError:
            bb_width, bb_height = font.get_bounding_box()
            bb_x_offset, bb_y_offset = 0, 0
        self._tb = TextBox(
            font=font, text=text,
            width=self.width-14, height=self.height,
            x=7, y=5+((bb_height+bb_y_offset)//2),
        )
        self.append(self._tb)

    @property
    def width(self) -> int:
        return self._tg.width * WINDOW_TILE_SIZE
        
    @property
    def height(self) -> int:
        return self._tg.height * WINDOW_TILE_SIZE
    
    @property
    def text(self) -> str:
        return self._tb.text
    
    @text.setter
    def text(self, value:str) -> None:
        self._tb.text = value

text_window = TextWindow(
    width=256, height=56,
    text="Hello, World! My name is Blinka, and I'm a snake. What would you like to ask me about?",
)
text_window.x = (graphics.display.width - text_window.width) // 2
text_window.y = (graphics.display.height - text_window.height) - 16
text_window.hidden = True
graphics.main_group.append(text_window)

# title text
title_label = Label(FONT_TITLE, text="Ssspeed Dating", color=0xffffff,)
title_label.anchor_point = (.5, .5)
title_label.anchored_position = (graphics.display.width//2, graphics.display.height//2)
graphics.overlay_group.append(title_label)

started = False
def start() -> None:
    # Hide title -> fade in -> slide snake in -> show text
    global started
    if not started:
        started = True
        title_label.hidden = True
        graphics.main_group.hidden = False
        engine.Fade(on_complete=lambda: engine.Animator(
            target=snake_tg,
            end=(124, snake_tg.y),
            on_complete=lambda: setattr(text_window, "hidden", False),
        ))

finished = False
def finish() -> None:
    # hide text -> slide snake out -> fade out
    global finished
    if not finished:
        finished = True
        text_window.hidden = True
        engine.Animator(
            target=snake_tg,
            end=(graphics.display.width, snake_tg.y),
            on_complete=lambda: engine.Fade(reverse=True),
        )

ACTION_SELECT = const(0)
ACTION_UP     = const(1)
ACTION_DOWN   = const(2)
ACTION_PAUSE  = const(3)
ACTION_QUIT   = const(4)

def do_action(action:int) -> None:
    if action == ACTION_SELECT:
        sound.play_sfx(sound.SFX_CLICK)
        if not started:
            start()
        else:
            finish()
    elif action == ACTION_QUIT:
        supervisor.reload()

async def mouse_task() -> None:
    while True:
        if (mouse := adafruit_usb_host_mouse.find_and_init_boot_mouse("bitmaps/cursor.bmp")) is not None:
            graphics.root_group.append(mouse.tilegrid)
            timeouts = 0
            while timeouts < 9999:
                pressed_btns = mouse.update()
                if pressed_btns is None:
                    timeouts += 1
                else:
                    timeouts = 0
                    if "left" in pressed_btns:
                        # TODO: define selected based on position
                        do_action(ACTION_SELECT)
                await asyncio.sleep(1/config.TARGET_FRAME_RATE)
            graphics.root_group.remove(mouse.tilegrid)
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
