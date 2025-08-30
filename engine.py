# SPDX-FileCopyrightText: 2025 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3
import displayio
import fontio
import math
from terminalio import FONT

from adafruit_display_text.text_box import TextBox

import config
import graphics
import sound

current_event = None

def update() -> None:
    if current_event is not None:
        current_event.update()

class Event:

    def __init__(self, on_complete:callable=None):
        self._on_complete = on_complete
        self._active = False

    @property
    def playing(self) -> bool:
        return self._active
    
    @property
    def on_complete(self) -> callable:
        return self._on_complete
    
    @on_complete.setter
    def on_complete(self, value:callable) -> None:
        self._on_complete = value

    def play(self) -> None:
        global current_event
        if current_event is not None:
            current_event.stop()
        self._active = True
        current_event = self

    def stop(self) -> None:
        self._active = False

    def update(self) -> None:
        pass
        
    def complete(self) -> None:
        global current_event
        self.stop()
        if current_event is self:
            current_event = None
        if callable(self._on_complete):
            self._on_complete()

class Sequence:
    def __init__(self, *events):
        self._events = []
        self._index = 0
        if len(events):
            for event in events:
                self.append(event)

    def append(self, event) -> None:
        if isinstance(event, Event):
            event.on_complete = self._next
        self._events.append(event)

    def remove(self, event) -> None:
        self._events.remove(event)

    def _next(self) -> None:
        if self._index + 1 < len(self._events):
            self._index += 1
            self.play()
        else:
            self.stop()
    
    @property
    def playing(self) -> bool:
        return self._active
    
    def play(self) -> None:
        self._active = True
        event = self._events[self._index]
        if isinstance(event, Event):
            event.play()
        elif callable(event):
            event()
            self._next()

    def stop(self) -> None:
        self._active = False
        event = self._events[self._index]
        if isinstance(event, Event):
            event.stop()

class Entity(Event):

    def __init__(self, parent:displayio.Group, **kwargs):
        super().__init__(**kwargs)
        self._parent = parent
        self._group = displayio.Group()

    def play(self) -> None:
        super().play()
        if self._group not in self._parent:
            self._parent.append(self._group)
    
    def complete(self) -> None:
        if self._group in self._parent:
            self._parent.remove(self._group)
        del self._group
        super().complete()

class Fade(Entity):

    def __init__(self, duration:float=1, reverse:bool=False, **kwargs):
        super().__init__(parent=graphics.overlay_group, **kwargs)
        self._speed = config.TARGET_FRAME_RATE // duration
        self._reverse = reverse
        self._index = 0
        self._counter = 0
        self._tg = displayio.TileGrid(
            bitmap=graphics.fade_bmp, pixel_shader=graphics.fade_palette,
            width=graphics.display.width//graphics.FADE_TILE_SIZE, height=graphics.display.height//graphics.FADE_TILE_SIZE,
            tile_width=graphics.FADE_TILE_SIZE, tile_height=graphics.FADE_TILE_SIZE,
            default_tile=0 if not reverse else graphics.FADE_TILES-1,
        )
        self._group.append(self._tg)

    def update(self) -> None:
        super().update()
        if self._active:
            self._counter += 1
            if self._counter > self._speed:
                self._index += 1
                if self._index < graphics.FADE_TILES:
                    self._update_tile()
                else:
                    self.complete()

    def _update_tile(self) -> None:
        index = self._index if not self._reverse else graphics.FADE_TILES-self._index-1
        for x in range(self._tg.width):
            for y in range(self._tg.height):
                self._tg[x, y] = index
    
    def complete(self) -> None:
        self._group.remove(self._tg)
        del self._tg
        super().complete()

class Animator(Event):

    def __init__(self, target:displayio.Group, end:tuple, start:tuple=None, duration:float=1, **kwargs):
        super().__init__(**kwargs)
        self._target = target
        if start is not None:
            self._start = start
            self._target.x, self._target.y = self._start[0], self._start[1]
        else:
            self._start = (self._target.x, self._target.y)
        self._end = end
        self._duration = int(config.TARGET_FRAME_RATE * duration)
        self._frames = 0
        self._velocity = tuple([int((self._end[i] - self._start[i]) / self._duration) for i in range(2)])

    @property
    def animating(self) -> bool:
        return self._frames <= self._duration

    def update(self) -> None:
        super().update()
        if self._active:
            if self.animating:
                self._target.x = (self._frames * self._velocity[0]) + self._start[0]
                self._target.y = (self._frames * self._velocity[1]) + self._start[1]
                self._frames += 1
            else:
                self._target.x, self._target.y = self._end
                self.complete()

DIALOG_LINE_WIDTH = ((graphics.display.width // graphics.WINDOW_TILE_SIZE) - 10) * graphics.WINDOW_TILE_SIZE

class Dialog(Entity):

    def __init__(self, text:str="", font:fontio.FontProtocol=FONT, voice:int=1, **kwargs):
        super().__init__(parent=graphics.upper_group, **kwargs)

        try:
            bb_width, bb_height, bb_x_offset, bb_y_offset = font.get_bounding_box()
        except ValueError:
            bb_width, bb_height = font.get_bounding_box()
            bb_x_offset, bb_y_offset = 0, 0

        words = text.split(" ")
        line_width = DIALOG_LINE_WIDTH // bb_width
        lines = []
        line = ""
        for word in words:
            if len(line) + len(word) + 1 > line_width:
                lines.append(line.rstrip())
                line = ""
            line += word + " "
        if len(line):
            lines.append(line.rstrip())

        text_width = max([len(x)+1 for x in lines]) * bb_width
        text_height = len(lines) * (bb_height + 4) - 4

        width = max(math.ceil(text_width / graphics.WINDOW_TILE_SIZE) + 2, 3)
        height = max(math.ceil(text_height / graphics.WINDOW_TILE_SIZE) + 2, 3)
        
        # setup window background grid
        self._tg = displayio.TileGrid(
            bitmap=graphics.window_bmp, pixel_shader=graphics.window_palette,
            width=width, height=height,
            tile_width=graphics.WINDOW_TILE_SIZE, tile_height=graphics.WINDOW_TILE_SIZE, default_tile=4,
        )
        self._group.append(self._tg)

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
        self._tb = TextBox(
            font=font, text=text,
            width=text_width, height=text_height,
            x=graphics.WINDOW_TILE_SIZE, y=graphics.WINDOW_TILE_SIZE+4,
        )
        self._group.append(self._tb)

        # set position
        self._group.x = (graphics.display.width - self.width) // 2
        self._group.y = (graphics.display.height - self.height) - 16

        # configure voice
        self._voice = voice
        self._voice_len = len(text) // 10
        self._voice_index = -1
        self._next_voice()

    def _next_voice(self) -> None:
        if self.voice_playing:
            self._voice_index += 1
            sound.play_voice(self._voice)

    @property
    def voice_playing(self) -> bool:
        return self._voice_index < self._voice_len

    @property
    def width(self) -> int:
        return self._tg.width * graphics.WINDOW_TILE_SIZE
        
    @property
    def height(self) -> int:
        return self._tg.height * graphics.WINDOW_TILE_SIZE
    
    @property
    def text(self) -> str:
        return self._tb.text
    
    def update(self) -> None:
        super().update()
        if self.voice_playing and not sound.is_voice_playing():
            self._next_voice()
    
    def complete(self) -> None:
        self._group.remove(self._tg)
        del self._tg
        self._group.remove(self._tb)
        del self._tb
        super().complete()
