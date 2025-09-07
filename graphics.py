# SPDX-FileCopyrightText: 2025 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3
import displayio
import fontio
import math
import supervisor
from terminalio import FONT
import vectorio

from adafruit_display_text.label import Label
from adafruit_display_text.text_box import TextBox
from adafruit_fruitjam.peripherals import request_display_config
import adafruit_imageload
import asyncio

displayio.release_displays()

COLOR_WHITE = 0xffffff
COLOR_PINK  = 0xffb6de
COLOR_RED   = 0xff0000
COLOR_BLACK = 0x000000

ROW_GAP     = 4

def copy_palette(palette:displayio.Palette) -> displayio.Palette:
    clone = displayio.Palette(len(palette))
    for i, color in enumerate(palette):
        # Add color to new_palette
        clone[i] = color
        # Set new_palette color index transparency
        if palette.is_transparent(i):
            clone.make_transparent(i)
    return clone

# setup display
request_display_config(320, 240)
display = supervisor.runtime.display
display.auto_refresh = False

# create root group
root_group = displayio.Group()
display.root_group = root_group
display.refresh()  # blank out screen

# create groups for game elements
main_group = displayio.Group()
main_group.hidden = True
root_group.append(main_group)

lower_group = displayio.Group()
main_group.append(lower_group)

upper_group = displayio.Group()
main_group.append(upper_group)

# create group for overlay elements
overlay_group = displayio.Group()
root_group.append(overlay_group)

async def refresh() -> None:
    # update display if any changes were made
    display.refresh()
    await asyncio.sleep(1/30)

# load the fade bitmap
fade_bmp, fade_palette = adafruit_imageload.load("bitmaps/fade.bmp")
fade_palette.make_transparent(1)
FADE_TILE_SIZE = fade_bmp.height
FADE_TILES = fade_bmp.width // FADE_TILE_SIZE

# load window image
window_bmp, window_palette = adafruit_imageload.load("bitmaps/window.bmp")
window_palette.make_transparent(1)
WINDOW_TILE_SIZE = 8

# mouse cursor
cursor = None
last_cursor_pos = (-1, -1)

def set_cursor(tilegrid:displayio.TileGrid) -> None:
    global cursor
    if cursor is not None:
        reset_cursor()
    cursor = tilegrid
    cursor.x = display.width // 2
    cursor.y = display.height // 2
    root_group.append(cursor)

def reset_cursor():
    global cursor, last_cursor_pos
    root_group.remove(cursor)
    cursor = None
    last_cursor_pos = (-1, -1)

def get_cursor_pos(moved:bool = False) -> tuple:
    global last_cursor_pos, cursor
    if cursor:
        cursor_pos = (cursor.x, cursor.y)
        if not moved or not all((cursor_pos[i] == last_cursor_pos[i] for i in range(len(cursor_pos)))):
            if moved:
                last_cursor_pos = cursor_pos
            return cursor_pos

DIALOG_LINE_WIDTH = ((display.width // WINDOW_TILE_SIZE) - 10) * WINDOW_TILE_SIZE

class Dialog(displayio.Group):

    def __init__(self, text:str, title:str="", title_right:bool=False, force_width:bool=False, font:fontio.FontProtocol=FONT, title_font:fontio.FontProtocol=FONT, **kwargs):
        super().__init__(**kwargs)

        bb_width, bb_height = font.get_bounding_box()[0:2]

        words = text.split(" ")
        desired_line_width = DIALOG_LINE_WIDTH // bb_width
        lines = []
        line = ""
        for word in words:
            if len(line) + len(word) + 1 > desired_line_width:
                lines.append(line.rstrip())
                line = ""
            line += word + " "
        if len(line):
            lines.append(line.rstrip())

        text_width = DIALOG_LINE_WIDTH if force_width else max([len(x)+1 for x in lines]) * bb_width
        text_height = len(lines) * (bb_height + ROW_GAP) - ROW_GAP

        width = max(math.ceil(text_width / WINDOW_TILE_SIZE) + 2, 3)
        height = max(math.ceil(text_height / WINDOW_TILE_SIZE) + 2, 3) + (2 if title else 0)
        
        # setup window background grid
        self._tg_palette = copy_palette(window_palette)
        self._tg_palette_default = self._tg_palette[2]
        self._tg = displayio.TileGrid(
            bitmap=window_bmp, pixel_shader=self._tg_palette,
            width=width, height=height,
            tile_width=WINDOW_TILE_SIZE, tile_height=WINDOW_TILE_SIZE, default_tile=14,
        )
        self.append(self._tg)

        # set corners
        self._tg[0, (2 if title else 0)] = (9 if title and not title_right else 0)
        self._tg[self._tg.width-1, (2 if title else 0)] = (13 if title and title_right else 2)
        self._tg[0, self._tg.height-1] = 6
        self._tg[self._tg.width-1, self._tg.height-1] = 8

        # set borders
        for x in range(1, self._tg.width-1):
            self._tg[x, (2 if title else 0)] = 1
            self._tg[x, self._tg.height-1] = 7
        for y in range(3 if title else 1, self._tg.height-1):
            self._tg[0, y] = 3
            self._tg[self._tg.width-1, y] = 5

        # fill space
        for x in range(1, self._tg.width-1):
            for y in range(3 if title else 1, self._tg.height-1):
                self._tg[x, y] = 4

        # set title area
        if title:
            title_width = math.ceil(title_font.get_bounding_box()[0] * len(title) / WINDOW_TILE_SIZE)
            self._tg[self._tg.width-title_width-2 if title_right else 0, 0] = 0
            self._tg[self._tg.width-title_width-2 if title_right else 0, 1] = 3
            self._tg[self._tg.width-1 if title_right else title_width+1, 0] = 2
            self._tg[self._tg.width-1 if title_right else title_width+1, 1] = 5
            self._tg[self._tg.width-title_width-2 if title_right else title_width+1, 2] = 12 if title_right else 11
            for x in range(self._tg.width-title_width-1 if title_right else 1, self._tg.width-1 if title_right else title_width+1):
                self._tg[x, 0] = 1
                self._tg[x, 1] = 4
                self._tg[x, 2] = 10

        # setup textbox
        self.append(TextBox(
            font=font, text=text,
            width=text_width, height=text_height,
            x=WINDOW_TILE_SIZE, y=WINDOW_TILE_SIZE*(3 if title else 1)+4,
        ))

        # setup title label
        if title:
            label = Label(
                font=title_font, text=title,
                x=WINDOW_TILE_SIZE, y=WINDOW_TILE_SIZE+3,
            )
            if title_right:
                label.anchored_position = (self.width-label.x, label.y)
                label.anchor_point = (1, .5)
            self.append(label)

        # set position
        self.x = (display.width - self.width) // 2
        self.y = (display.height - self.height) - 16

    @property
    def width(self) -> int:
        return self._tg.width * WINDOW_TILE_SIZE
        
    @property
    def height(self) -> int:
        return self._tg.height * WINDOW_TILE_SIZE
    
    def contains(self, x:int, y:int) -> bool:
        return self._tg.contains((x - self.x, y - self.y, 0))
    
    def hover(self, value:bool) -> None:
        self._tg_palette[2] = COLOR_RED if value else self._tg_palette_default

class Heart(displayio.Group):

    def __init__(self, size:int, color:int=COLOR_PINK, **kwargs):
        super().__init__(**kwargs)

        palette = displayio.Palette(1)
        palette[0] = color

        left_circle = vectorio.Circle(
            pixel_shader=palette, radius=size//4,
            x=-size//4, y=-size//4,
        )
        self.append(left_circle)

        right_circle = vectorio.Circle(
            pixel_shader=palette, radius=size//4,
            x=size//4, y=-size//4,
        )
        self.append(right_circle)

        angle = math.pi / 4
        x = int(right_circle.x + right_circle.radius * math.cos(angle))
        y = int(right_circle.y + right_circle.radius * math.sin(angle))

        self.append(vectorio.Polygon(
            pixel_shader=palette,
            points=[
                (size//2, -size//4),
                (x, y),
                (0, size//2),
                (-x, y),
                (-size//2, -size//4),
            ],
        ))

class Button(displayio.Group):

    def __init__(self, text:str="", font:fontio.FontProtocol=FONT, width:int=16, height:int=16, border:int=1, color:int=COLOR_PINK, color_hover:int=COLOR_WHITE, background_color:int=COLOR_BLACK, **kwargs):
        super().__init__(**kwargs)
        
        self._color = color
        self._color_hover = color_hover

        self._outline_palette = displayio.Palette(1)
        self._outline_palette[0] = color
        
        self._outline = vectorio.Rectangle(
            pixel_shader=self._outline_palette,
            width=width, height=height,
        )
        self.append(self._outline)

        self._background_palette = displayio.Palette(1)
        self._background_palette[0] = background_color

        self._background = vectorio.Rectangle(
            pixel_shader=self._background_palette,
            width=width-border*2, height=height-border*2,
            x=border, y=border,
        )
        self.append(self._background)

        self._label = Label(
            text=text, font=font, color=color,
            anchor_point=(.5, .5),
            anchored_position=(width//2, height//2),
        )
        self.append(self._label)
    
    def contains(self, x:int, y:int) -> bool:
        return 0 <= x - self.x <= self._outline.width and 0 <= y - self.y <= self._outline.height
    
    @property
    def hover(self) -> bool:
        return self._outline_palette == self._color_hover
    
    @hover.setter
    def hover(self, value:bool) -> None:
        color = self._color_hover if value else self._color
        self._outline_palette[0] = color
        self._label.color = color

    @property
    def text(self) -> str:
        return self._label.text
    
    @text.setter
    def text(self, value:str) -> None:
        self._label.text = value
