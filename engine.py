# SPDX-FileCopyrightText: 2025 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3
import displayio

import adafruit_imageload

import config
import graphics

# create list which will hold all game objects
class Entities(list):

    def __init__(self):
        super().__init__()

    def update(self) -> None:
        for x in self:
            x.update()

entities = Entities()

class Entity(displayio.Group):

    def __init__(self, on_complete:callable=None, **kwargs):
        global entities
        super().__init__(**kwargs)
        if self not in entities:
            entities.append(self)
        self._on_complete = on_complete

    def update(self) -> None:
        pass
    
    def complete(self) -> None:
        global entities
        if self in entities:
            entities.remove(self)
        if self._on_complete is not None and callable(self._on_complete):
            self._on_complete()
        del self

    @property
    def active(self) -> bool:
        global entities
        return self in entities
    
    @property
    def on_complete(self) -> callable:
        return self._on_complete
    
    @on_complete.setter
    def on_complete(self, value:callable) -> None:
        self._on_complete = value

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
        self._active = True

    def stop(self) -> None:
        self._active = False
        
    def complete(self) -> None:
        self.stop()
        if callable(self._on_complete):
            self._on_complete()

class Sequence(Event):
    def __init__(self, *events):
        super().__init__()
        self._events = list(events)
        self._index = 0
        self._active = False
        if len(events):
            for event in events:
                self.append(event)

    def append(self, event) -> None:
        event.on_complete = self._next
        self._events.append(event)

    def remove(self, event) -> None:
        self._events.remove(event)
    
    @property
    def playing(self) -> bool:
        return self._active
    
    def play(self) -> None:
        pass

    def stop(self) -> None:
        pass

# load the fade bitmap
fade_bmp, fade_palette = adafruit_imageload.load("bitmaps/fade.bmp")
fade_palette.make_transparent(1)
FADE_TILE_SIZE = fade_bmp.height
FADE_TILES = fade_bmp.width // FADE_TILE_SIZE

class Fade(Entity):
    def __init__(self, duration:float=1, reverse:bool=False, **kwargs):
        global fade_bmp, fade_palette
        super().__init__(**kwargs)
        self._speed = config.TARGET_FRAME_RATE // duration
        self._reverse = reverse
        self._index = 0
        self._counter = 0
        self._tg = displayio.TileGrid(
            bitmap=fade_bmp, pixel_shader=fade_palette,
            width=graphics.display.width//FADE_TILE_SIZE, height=graphics.display.height//FADE_TILE_SIZE,
            tile_width=FADE_TILE_SIZE, tile_height=FADE_TILE_SIZE,
            default_tile=0 if not reverse else FADE_TILES-1,
        )
        self.append(self._tg)
        graphics.overlay_group.append(self)

    def update(self) -> None:
        super().update()
        if self.active:
            self._counter += 1
            if self._counter > self._speed:
                self._index += 1
                if self._index < FADE_TILES:
                    self._update_tile()
                else:
                    self.complete()

    def _update_tile(self) -> None:
        index = self._index if not self._reverse else FADE_TILES-self._index-1
        for x in range(self._tg.width):
            for y in range(self._tg.height):
                self._tg[x, y] = index

    def __del__(self) -> None:
        self.remove(self._tg)
        del self._tg
        graphics.overlay_group.remove(self)
        super().__del__()

class Animator(Entity):
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
        if self.active:
            if self.animating:
                self._target.x = (self._frames * self._velocity[0]) + self._start[0]
                self._target.y = (self._frames * self._velocity[1]) + self._start[1]
                self._frames += 1
            else:
                self._target.x, self._target.y = self._end
                self.complete()

def update() -> None:
    # update all game entities
    entities.update()
