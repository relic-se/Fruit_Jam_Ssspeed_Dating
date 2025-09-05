# SPDX-FileCopyrightText: 2025 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3
import displayio
import fontio
import json
import random
import re
import supervisor
from terminalio import FONT
import vectorio

from adafruit_display_text.label import Label
import adafruit_imageload
from font_knewave_webfont_24 import FONT as FONT_TITLE

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

    def select(self) -> None:
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

    def __init__(self, speed:int=2, reverse:bool=False, **kwargs):
        super().__init__(parent=graphics.overlay_group, **kwargs)
        self._speed = speed
        self._reverse = reverse
        self._index = 0
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
        self._index += self._speed
        if self._index < graphics.FADE_TILES:
            self._update_tile()
        else:
            self.complete()

    def _update_tile(self) -> None:
        index = self._index if not self._reverse else graphics.FADE_TILES-self._index-1
        for x in range(self._tg.width):
            for y in range(self._tg.height):
                self._tg[x, y] = index

    def select(self) -> None:
        super().select()
        self.complete()
    
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
        self._duration = int(30 * duration)
        self._frames = 0
        self._velocity = tuple([int((self._end[i] - self._start[i]) / self._duration) for i in range(2)])

    @property
    def animating(self) -> bool:
        return self._frames <= self._duration

    def update(self) -> None:
        super().update()
        if self.animating:
            self._target.x = (self._frames * self._velocity[0]) + self._start[0]
            self._target.y = (self._frames * self._velocity[1]) + self._start[1]
            self._frames += 1
        else:
            self._target.x, self._target.y = self._end
            self.complete()

    def select(self) -> None:
        super().select()
        self.complete()
    
    def complete(self) -> None:
        self._target.x, self._target.y = self._end
        super().complete()

command_regex = re.compile("\[(\w+)\]")

class VoiceDialog(Entity):

    def __init__(self, text:str, voice:bool=True, on_complete:callable=None, **kwargs):
        while (command := command_regex.search(text)):
            replace = ""
            if command.group(1) == "name":
                replace = scene.player_name
            elif command.group(1) == "buzzer":
                sound.play_sfx(sound.SFX_BUZZER)
            elif command.group(1) == "quiet":
                voice = False
                kwargs["title"] = ""
            text = text[:command.start(0)] + replace + text[command.end(0):]
        text = text.strip()

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
        if voice:
            self._next_voice()

    def _next_voice(self) -> None:
        if self.voice_playing:
            self._voice_index += 1
            sound.play_voice()

    @property
    def voice_playing(self) -> bool:
        return self._voice and self._voice_index < self._voice_len

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

    def __init__(self, options:list, shuffle:bool=True, **kwargs):
        super().__init__(parent=graphics.upper_group, **kwargs)

        # shuffle options
        if shuffle:
            self._options = []
            while len(options):
                index = random.randint(0, len(options)-1)
                option = options.pop(index)
                self._options.append(option)
        else:
            self._options = options

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

            if scene.current_scene is not None and hasattr(scene.current_scene, "score"):
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
                title=scene.player_name, voice=False,
                on_complete=self._next_extra_dialog,
            ).play()

    def _next_response_dialog(self) -> None:
        self._response_index += 1
        if self._response_index >= len(self._response):
            self.complete()
        else:
            VoiceDialog(
                self._response[self._response_index],
                title=(scene.current_scene.name if scene.current_scene is not None else ""),
                title_right=True,
                voice=True,
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

        for index, filename in enumerate(scene.LEVELS):
            name = filename[len("00-"):-len(".json")]
            with open("content/" + filename, "r") as f:
                data = json.load(f)
                name = data.get("name", name)

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

KEYBOARD_CHARS = (
    ("q", "w", "e", "r", "t", "y", "u", "i", "o", "p"),
    ("a", "s", "d", "f", "g", "h", "j", "k", "l"),
    ("z", "x", "c", "v", "b", "n", "m"),
)

class Keyboard(Entity):

    def __init__(self, font:fontio.FontProtocol=FONT_TITLE, size:int=16, gap:int=2, margin:int=4, max_length:int=16, **kwargs):
        super().__init__(parent=graphics.overlay_group, **kwargs)
        self._max_length = max(max_length, 1)

        keys_height = len(KEYBOARD_CHARS) * (size + gap) - gap
        bb_height = font.get_bounding_box()[1]
        height = keys_height + margin + bb_height

        # setup graph background grid
        tg = displayio.TileGrid(
            bitmap=graphics.window_bmp, pixel_shader=graphics.window_palette,
            width=graphics.display.width//graphics.WINDOW_TILE_SIZE,
            height=height//graphics.WINDOW_TILE_SIZE+2,
            tile_width=graphics.WINDOW_TILE_SIZE, tile_height=graphics.WINDOW_TILE_SIZE, default_tile=4,
        )
        tg.y = graphics.display.height - tg.height * graphics.WINDOW_TILE_SIZE
        for x in range(0, tg.width):
            tg[x, 0] = 1 # top border
        self._group.append(tg)

        self._keys = displayio.Group()
        self._group.append(self._keys)

        for y, row in enumerate(KEYBOARD_CHARS):
            row_width = (len(row) - 1) * (size + gap) - gap
            for x, char in enumerate(row):
                self._keys.append(graphics.Key(
                    text=char, size=size,
                    x=(graphics.display.width - row_width)//2 + x*(size + gap),
                    y=graphics.display.height - graphics.WINDOW_TILE_SIZE - keys_height + y*(size + gap),
                ))

        self._text = Label(
            font=FONT_TITLE, text="",
            anchor_point=(.5, .5),
            anchored_position=(
                graphics.display.width//2,
                graphics.display.height - graphics.WINDOW_TILE_SIZE - keys_height - margin - bb_height//2
            )
        )
        self._group.append(self._text)

        mid_row_width = (len(KEYBOARD_CHARS[1]) - 1) * (size + gap) - gap

        self._upper = graphics.Key(
            text="^", size=size,
            x=(graphics.display.width - mid_row_width)//2 - gap - size,
            y=graphics.display.height - graphics.WINDOW_TILE_SIZE - size*2 - gap,
        )
        self._group.append(self._upper)

        self._back = graphics.Key(
            text="<", size=size,
            x=(graphics.display.width + mid_row_width)//2 + gap,
            y=graphics.display.height - graphics.WINDOW_TILE_SIZE - size*2 - gap,
        )
        self._group.append(self._back)

        self._enter = graphics.Key(
            text=">", size=size,
            x=graphics.display.width - graphics.WINDOW_TILE_SIZE - size,
            y=graphics.display.height - graphics.WINDOW_TILE_SIZE - size,
        )
        self._enter.hidden = True
        self._group.append(self._enter)

    @property
    def upper(self) -> bool:
        return self._keys[0].text.isupper()
    
    @upper.setter
    def upper(self, value:bool) -> None:
        for key in self._keys:
            if value:
                key.text = key.text.upper()
            else:
                key.text = key.text.lower()

    def update(self) -> None:
        super().update()
        if graphics.cursor:
            cursor_pos = graphics.get_cursor_pos()
            for key in self._keys:
                key.hover = key.contains(cursor_pos)
            for key in (self._upper, self._back, self._enter):
                key.hover = key.contains(cursor_pos)

    def select(self) -> None:
        super().select()
        if graphics.cursor:
            cursor_pos = graphics.get_cursor_pos()
            for key in self._keys:
                if key.contains(cursor_pos):
                    self._text.text += key.text
                    if len(self._text.text) > self._max_length:
                        self._text.text = self._text.text[:self._max_length]
                    if self.upper:
                        self.upper = False
                    if self._enter.hidden:
                        self._enter.hidden = False
                    break
            
            if self._upper.contains(cursor_pos):
                self.upper = not self.upper

            text = self._text.text
            if self._back.contains(cursor_pos) and len(text) > 1:
                self._text.text = text[:len(text)-2]  # don't know why this needs to be 2, Label is adding a "l" to the end
                if not len(self._text.text):
                    self._enter.hidden = True

            if not self._enter.hidden and self._enter.contains(cursor_pos):
                self.complete()
    
    def complete(self) -> None:
        # save name
        scene.player_name = self._text.text

        self._group.remove(self._keys)
        del self._keys
        for key in (self._upper, self._back, self._enter):
            self._group.remove(key)
            del key
        self._group.remove(self._text)
        del self._text
        super().complete()
