# SPDX-FileCopyrightText: 2025 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3
import displayio
import random
import supervisor
from terminalio import FONT
import vectorio

from adafruit_display_text.label import Label
import adafruit_imageload
from font_knewave_webfont_24 import FONT as FONT_TITLE

import config
import graphics
import scene
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

    def select(self) -> None:
        pass

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

    def play(self) -> None:
        super().play()
        if not self._reverse:
            graphics.main_group.hidden = False

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
        if self._reverse:
            graphics.main_group.hidden = True
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

class VoiceDialog(Entity):

    def __init__(self, text:str, voice:int=1, on_complete:callable=None, **kwargs):
        command = None
        if text.startswith("_"):
            command = "_"
        elif text.startswith("[buzzer]"):
            command = "[buzzer]"
            sound.play_sfx(sound.SFX_BUZZER)
        if command is not None:
            voice = 0
            text = text[len(command):].lstrip()
            kwargs["title"] = ""

        super().__init__(parent=graphics.upper_group, on_complete=on_complete)

        self._dialog = graphics.Dialog(text, **kwargs)
        self._group.append(self._dialog)

        # arrow indicator
        self._group.append(Label(
            font=FONT, text=">",
            anchor_point=(.5, 1),
            anchored_position=(
                self._dialog.x + self._dialog.width - graphics.WINDOW_TILE_SIZE,
                self._dialog.y + self._dialog.height - graphics.WINDOW_TILE_SIZE//2
            ),
        ))

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

    def update(self) -> None:
        super().update()
        if self.voice_playing and not sound.is_voice_playing():
            self._next_voice()
        # TODO: Handle mouse hover?
    
    def select(self) -> None:
        super().select()
        self.complete()

    def complete(self) -> None:
        self._group.remove(self._dialog)
        del self._dialog
        super().complete()

class OptionDialog(Entity):

    def __init__(self, options:list, **kwargs):
        super().__init__(parent=graphics.upper_group, **kwargs)

        # shuffle options
        self._options = []
        while len(options):
            index = random.randint(0, len(options)-1)
            option = options.pop(index)
            self._options.append(option)

        self._dialogs = []
        for option in self._options:
            message = option if type(option) is str else option.get("message", "")
            dialog = graphics.Dialog(message[0] if type(message) is list else message, force_width=True)
            self._dialogs.append(dialog)
            self._group.append(dialog)
        
        y = graphics.display.height - 8
        for dialog in reversed(self._dialogs):
            y -= dialog.height + 8
            dialog.y = y

        self._extra = None
        self._extra_index = -1

        self._response = None
        self._response_index = -1

    def update(self) -> None:
        super().update()
        if graphics.cursor:
            cursor_pos = graphics.get_cursor_pos()
            for dialog in self._dialogs:
                dialog.hover(dialog.contains(cursor_pos))

    def select(self) -> None:
        super().select()

        index = None
        if graphics.cursor:
            cursor_pos = graphics.get_cursor_pos()
            for dialog_index, dialog in enumerate(self._dialogs):
                if dialog.contains(cursor_pos):
                    index = dialog_index
                    break
        if index is None:
            return
        
        selected = min(max(index, 0), len(self._options))

        # hide dialog options
        for dialog in self._dialogs:
            self._group.remove(dialog)

        option = self._options[selected]
        if type(option) is dict:

            if scene.current_scene is not None:
                scene.current_scene.score += option.get("score", 0)

            if type(option.get("message")) is list:
                self._extra = option.get("message")[1:]

            if type(option.get("response")) in (list, str):
                self._response = option.get("response")
                if type(self._response) is str:
                    self._response = [self._response]
        
        if self._extra is not None:
            self._next_extra_dialog()
        elif self._response is not None:
            self._next_response_dialog()
        else:
            self.complete()

    def _next_extra_dialog(self) -> None:
        self._extra_index += 1
        if self._extra_index >= len(self._extra):
            if self._response is not None:
                self._next_response_dialog()
            else:
                self.complete()
        else:
            VoiceDialog(
                self._extra[self._extra_index],
                title="You", voice=0,
                on_complete=self._next_extra_dialog,
            ).play()

    def _next_response_dialog(self) -> None:
        self._response_index += 1
        if self._response_index >= len(self._response):
            self.complete()
        else:
            VoiceDialog(
                self._response[self._response_index],
                title=(scene.current_scene.title if scene.current_scene is not None else ""),
                title_right=True,
                voice=(scene.current_scene.voice if scene.current_scene is not None else 0),
                on_complete=self._next_response_dialog,
            ).play()
    
    def complete(self) -> None:
        del self._dialogs
        super().complete()

class Results(Entity):

    def __init__(self):
        super().__init__(parent=graphics.upper_group)

        # background heart
        self._group.append(graphics.Heart(
            size=graphics.display.width//4,
            x=graphics.display.width//2,
            y=graphics.display.height//4,
        ))

        # setup graph background grid
        tg = displayio.TileGrid(
            bitmap=graphics.window_bmp, pixel_shader=graphics.window_palette,
            width=graphics.display.width//graphics.WINDOW_TILE_SIZE,
            height=graphics.display.height//2//graphics.WINDOW_TILE_SIZE,
            y=graphics.display.height//2,
            tile_width=graphics.WINDOW_TILE_SIZE, tile_height=graphics.WINDOW_TILE_SIZE, default_tile=4,
        )
        for x in range(0, tg.width):
            tg[x, 0] = 1 # top border
        self._group.append(tg)

        # setup title label
        self._group.append(Label(
            font=FONT_TITLE, text="Thanks for Playing!",
            anchor_point=(.5, .5),
            anchored_position=(graphics.display.width//2, graphics.display.height//4),
        ))

        # setup level graphs
        max_score, min_score = max(scene.level_scores), min(scene.level_scores)
        score_range = max_score - min_score

        width = graphics.display.width//len(scene.LEVELS)
        label_y = graphics.display.height - 16
        bar_height = graphics.display.height//4
        bar_width = 16
        bar_y = graphics.display.height - 32

        for index, name in enumerate(scene.LEVELS):
            score = scene.level_scores[index] - min_score
            x = width * index + width // 2

            label = Label(
                font=FONT, text=(name[0].upper()+name[1:]),
                anchor_point=(.5, .5),
                anchored_position=(x, label_y),
            )
            self._group.append(label)

            bar_palette = displayio.Palette(1)
            bar_palette[0] = (min(0xff * (score_range - score) * 2 // score_range, 0xff) << 16) | (min(0xff * score * 2 // score_range, 0xff) << 8)
            bar = vectorio.Rectangle(
                pixel_shader=bar_palette,
                width=bar_width,
                height=max(bar_height * score // score_range, 2),
                x=x-bar_width//2, y=bar_y,
            )
            bar.y -= bar.height
            self._group.append(bar)

        # setup arrow indicator
        self._group.append(Label(
            font=FONT, text=">",
            anchor_point=(1, 0),
            anchored_position=(graphics.display.width-8, graphics.display.height//2+graphics.WINDOW_TILE_SIZE),
        ))

    def select(self) -> None:
        super().select()
        self.complete()

def label_contains(label:Label, touch_tuple:tuple) -> bool:
    x, y, w, h = label.bounding_box
    x += label.x
    y += label.y
    tx, ty, _t = touch_tuple
    return 0 <= tx - x <= w and 0 <= ty - y <= h

class Title(Entity):

    def __init__(self):
        super().__init__(parent=graphics.overlay_group)

        # background heart
        self._group.append(graphics.Heart(
            size=max(graphics.display.width, graphics.display.height)//2,
            x=graphics.display.width//2,
            y=graphics.display.height//2,
        ))

        # snake silhouette
        bitmap, palette = adafruit_imageload.load("bitmaps/title.bmp")
        palette.make_transparent(1)
        self._group.append(displayio.TileGrid(
            bitmap=bitmap, pixel_shader=palette,
            x=(graphics.display.width-bitmap.width)//2,
            y=(graphics.display.height-bitmap.height)//2,
        ))

        # title text
        self._group.append(Label(
            font=FONT_TITLE, text="Ssspeed Dating",
            anchor_point=(.5, .5),
            anchored_position=(graphics.display.width//2, graphics.display.height//2),
        ))

        self._start_label = Label(
            font=FONT_TITLE, text="Play", color=graphics.COLOR_PINK,
            anchor_point=(.5, .5),
            anchored_position=(graphics.display.width//4, graphics.display.height*3//4),
        )
        self._group.append(self._start_label)

        self._quit_label = Label(
            font=FONT_TITLE, text="Quit", color=graphics.COLOR_PINK,
            anchor_point=(.5, .5),
            anchored_position=(graphics.display.width*3//4, graphics.display.height*3//4),
        )
        self._group.append(self._quit_label)

    def update(self) -> None:
        super().update()
        if graphics.cursor:
            cursor_pos = graphics.get_cursor_pos()
            for label in (self._start_label, self._quit_label):
                contains = label_contains(label, cursor_pos)
                if label.color == graphics.COLOR_PINK and contains:
                    label.color = graphics.COLOR_WHITE
                elif label.color == graphics.COLOR_WHITE and not contains:
                    label.color = graphics.COLOR_PINK

    def select(self) -> None:
        super().select()
        if graphics.cursor:
            cursor_pos = graphics.get_cursor_pos()
            if label_contains(self._start_label, cursor_pos):
                self.complete()
            elif label_contains(self._quit_label, cursor_pos):
                supervisor.reload()
    
    def complete(self) -> None:
        self._group.remove(self._start_label)
        del self._start_label
        self._group.remove(self._quit_label)
        del self._quit_label
        super().complete()
