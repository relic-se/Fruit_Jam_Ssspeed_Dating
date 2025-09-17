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

events = []

def update() -> None:
    global events
    cursor_pos = graphics.get_cursor_pos(True)
    for event in events:
        event.update()
        if cursor_pos is not None and event.mousemove(*cursor_pos):
            break

def mouseclick() -> None:
    global events
    sound.play_sfx(sound.SFX_CLICK)
    pos = graphics.get_cursor_pos()
    if pos is not None:
        for event in events:
            if event.mouseclick(*pos) is True:
                break

def up() -> None:
    global events
    for event in events:
        if event.up() is True:
            break

def down() -> None:
    global events
    for event in events:
        if event.down() is True:
            break

def left() -> None:
    global events
    for event in events:
        if event.left() is True:
            break

def right() -> None:
    global events
    for event in events:
        if event.right() is True:
            break

def select() -> None:
    global events
    sound.play_sfx(sound.SFX_CLICK)
    for event in events:
        if event.select() is True:
            break

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
        global events
        self._active = True
        events.append(self)

    def stop(self) -> None:
        global events
        self._active = False
        if self in events:
            events.remove(self)

    def update(self) -> None:
        pass

    def mousemove(self, x:int, y:int) -> bool:  # True = stop propagation
        pass

    def mouseclick(self, x:int, y:int) -> bool:  # True = stop propagation
        self.select()
        return True
    
    def up(self) -> bool:  # True = stop propagation
        pass
    
    def down(self) -> bool:  # True = stop propagation
        pass
    
    def left(self) -> bool:  # True = stop propagation
        return self.up()
    
    def right(self) -> bool:  # True = stop propagation
        return self.down()

    def select(self) -> bool:
        self.complete()
        
    def complete(self) -> None:
        self.stop()
        if callable(self._on_complete):
            self._on_complete()

def get_event(event_class) -> Event:
    global events
    for event in events:
        if isinstance(event, event_class):
            return event
        
def has_event(event_class) -> bool:
    return get_event(event_class) is not None

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
    
    def stop(self) -> None:
        if self._group in self._parent:
            self._parent.remove(self._group)
        del self._group
        super().stop()

class Fade(Entity):

    def __init__(self, speed:int=2, reverse:bool=False, initial:int=0, **kwargs):
        super().__init__(parent=graphics.overlay_group, **kwargs)
        self._speed = speed
        self._reverse = reverse
        self._index = min(max(initial, 0), graphics.FADE_TILES-1)
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

    def stop(self) -> None:
        if self._reverse:
            graphics.main_group.hidden = True
        self._group.remove(self._tg)
        del self._tg
        super().stop()

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
        if self.animating:
            self._target.x = (self._frames * self._velocity[0]) + self._start[0]
            self._target.y = (self._frames * self._velocity[1]) + self._start[1]
            self._frames += 1
        else:
            self._target.x, self._target.y = self._end
            self.complete()
    
    def complete(self) -> None:
        self._target.x, self._target.y = self._end
        super().complete()

command_regex = re.compile("\[(\w+)\]")

class VoiceDialog(Entity):

    def __init__(self, text:str, voice:bool|str=True, on_complete:callable=None, **kwargs):
        announcer = False
        while (command := command_regex.search(text)):
            replace = ""
            if command.group(1) == "name":
                replace = scene.player_name
            elif command.group(1) == "buzzer":
                sound.play_sfx(sound.SFX_BUZZER)
            elif command.group(1) == "quiet":
                voice = False
                kwargs["title"] = ""
            elif command.group(1) == "player":
                voice = False
                kwargs["title"] = scene.player_name
                kwargs["title_right"] = False
            elif command.group(1) == "announcer":
                voice = "blinka"
                kwargs["title"] = "Blinka"
                kwargs["title_right"] = False
                announcer = True
            text = text[:command.start(0)] + replace + text[command.end(0):]
        text = text.strip()

        super().__init__(parent=graphics.upper_group, on_complete=on_complete)

        if announcer:
            bitmap, palette = adafruit_imageload.load("bitmaps/announcer.bmp")
            palette.make_transparent(4)
            self._group.append(displayio.TileGrid(
                bitmap=bitmap, pixel_shader=palette,
                x=8, y=8,
            ))

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
        if voice is True and scene.current_scene is not None and hasattr(scene.current_scene, "voice"):
            self._voice = scene.current_scene.voice
        else:
            self._voice = voice if type(voice) is str else False
        self._voice_len = len(text) // 10
        self._voice_index = -1
        if voice:
            self._next_voice()

    def _next_voice(self) -> None:
        if self.voice_playing:
            self._voice_index += 1
            sound.play_voice(self._voice)

    @property
    def voice_playing(self) -> bool:
        return self._voice is not False and self._voice_index < self._voice_len

    def update(self) -> None:
        if self.voice_playing and not sound.is_voice_playing():
            self._next_voice()

    def stop(self) -> None:
        self._group.remove(self._dialog)
        del self._dialog
        super().stop()

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
            if type(message) is list:
                message = message[0]

            # handle commands
            while (command := command_regex.search(message)):
                replace = ""
                if command.group(1) == "name":
                    replace = scene.player_name
                message = message[:command.start(0)] + replace + message[command.end(0):]
            message = message.strip()

            dialog = graphics.Dialog(message, force_width=True)
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

        self._index = None

    def mousemove(self, x:int, y:int) -> bool:
        if self._dialogs is not None:
            for dialog in self._dialogs:
                contains = dialog.contains(x, y)
                dialog.hover(contains)
                if contains:
                    self._index = None  # reset keyboard control

    def mouseclick(self, x:int, y:int) -> bool:
        if self._dialogs is not None:
            for index, dialog in enumerate(self._dialogs):
                if dialog.contains(x, y):
                    self.select(index)
                    return True
                
    def up(self) -> bool:
        if self._index is None:
            self._index = len(self._dialogs) - 1
        else:
            self._index = (self._index - 1) % len(self._dialogs)
        for index, dialog in enumerate(self._dialogs):
            dialog.hover(index == self._index)

    def down(self) -> bool:
        if self._index is None:
            self._index = 0
        else:
            self._index = (self._index + 1) % len(self._dialogs)
        for index, dialog in enumerate(self._dialogs):
            dialog.hover(index == self._index)

    def select(self, index:int = None) -> bool:
        if index is None and self._index is not None:
            index = self._index
        if self._dialogs is not None and index is not None and 0 <= index < len(self._options):
            option = self._options[index]

            # remove dialog options
            for dialog in self._dialogs:
                self._group.remove(dialog)
            del self._dialogs
            self._dialogs = None

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
                title=(scene.current_scene.name if scene.current_scene is not None and hasattr(scene.current_scene, "name") else ""),
                title_right=True,
                voice=True,
                on_complete=self._next_response_dialog,
            ).play()

    def stop(self) -> None:
        if self._dialogs is not None:
            for dialog in self._dialogs:
                self._group.remove(dialog)
            del self._dialogs
        super().stop()

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
        for i in range(2):  # 0=shadow, 1=top
            offset = (1 - i) * 2
            self._group.append(Label(
                font=FONT_TITLE, text="Thanks for Playing!",
                color=0xffffff * i,
                anchor_point=(.5, .5),
                anchored_position=(graphics.display.width//2+offset, graphics.display.height//4+offset),
            ))

        # setup level graphs
        max_score, min_score = max(scene.level_scores), min(scene.level_scores)
        score_range = max_score - min_score

        if score_range > 0:
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

                self._group.append(Label(
                    font=FONT, text=(name[0].upper()+name[1:]),
                    anchor_point=(.5, .5),
                    anchored_position=(x, label_y),
                ))

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

def label_contains(label:Label, x:int, y:int) -> bool:
    bb_x, bb_y, bb_w, bb_h = label.bounding_box
    bb_x += label.x
    bb_y += label.y
    return 0 <= x - bb_x <= bb_w and 0 <= y - bb_y <= bb_h

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

        # menu labels
        self._labels = []

        self._start_label = Label(
            font=FONT_TITLE, text="Play", color=graphics.COLOR_PINK,
            anchor_point=(.5, .5),
            anchored_position=(graphics.display.width//4, graphics.display.height*3//4),
        )
        self._group.append(self._start_label)
        self._labels.append(self._start_label)

        self._quit_label = Label(
            font=FONT_TITLE, text="Quit", color=graphics.COLOR_PINK,
            anchor_point=(.5, .5),
            anchored_position=(graphics.display.width*3//4, graphics.display.height*3//4),
        )
        self._group.append(self._quit_label)
        self._labels.append(self._quit_label)

        # credits text
        self._group.append(Label(
            font=FONT, text="a game by cooper & sam", color=0x666666,
            anchor_point=(.5, 1),
            anchored_position=(graphics.display.width//2, graphics.display.height-2),
        ))

        self._index = None

    def _label_hover(self, label:Label, contains:bool) -> None:
        if label.color == graphics.COLOR_PINK and contains:
            label.color = graphics.COLOR_WHITE
        elif label.color == graphics.COLOR_WHITE and not contains:
            label.color = graphics.COLOR_PINK

    def _label_select(self, index:int) -> bool:
        if index == 0:  # start
            self.complete()
            return True
        elif index == 1:  # quit
            supervisor.reload()

    def mousemove(self, x:int, y:int) -> None:
        for label in self._labels:
            contains = label_contains(label, x, y)
            self._label_hover(label, contains)
            if contains:
                self._index = None  # reset keyboard position

    def mouseclick(self, x:int, y:int) -> None:
        for index, label in enumerate(self._labels):
            if label_contains(label, x, y):
                return self._label_select(index)

    def up(self) -> bool:
        if self._index is None:
            self._index = len(self._labels) - 1
        else:
            self._index = (self._index - 1) % len(self._labels)
        for index, label in enumerate(self._labels):
            self._label_hover(label, self._index == index)

    def down(self) -> bool:
        if self._index is None:
            self._index = 0
        else:
            self._index = (self._index + 1) % len(self._labels)
        for index, label in enumerate(self._labels):
            self._label_hover(label, self._index == index)

    def select(self, index:int=None) -> bool:
        if index is None and self._index is not None:
            index = self._index
        if index is not None:
            return self._label_select(index)

    def stop(self) -> None:
        self._group.remove(self._start_label)
        del self._start_label
        self._group.remove(self._quit_label)
        del self._quit_label
        super().stop()

KEYBOARD_CHARS = (
    ("q", "w", "e", "r", "t", "y", "u", "i", "o", "p"),
    ("^", "a", "s", "d", "f", "g", "h", "j", "k", "l", "<"),
    ("z", "x", "c", "v", "b", "n", "m", ">"),
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
        for y, row in enumerate(KEYBOARD_CHARS):
            row_width = len(row) * (size + gap) - gap
            for x, char in enumerate(row):
                self._keys.append(graphics.Button(
                    text=char, width=size, height=size,
                    x=(graphics.display.width - row_width)//2 + x*(size + gap),
                    y=graphics.display.height - graphics.WINDOW_TILE_SIZE - keys_height + y*(size + gap),
                ))
        self._keys[-1].hidden = True
        self._group.append(self._keys)

        self._text = Label(
            font=FONT_TITLE, text="",
            anchor_point=(.5, .5),
            anchored_position=(
                graphics.display.width//2,
                graphics.display.height - graphics.WINDOW_TILE_SIZE - keys_height - margin - bb_height//2
            )
        )
        self._group.append(self._text)

        self._column, self._row = None, None

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

    def append(self, value:str) -> None:
        if value.isalpha():
            self._text.text += value
            if len(self._text.text) > self._max_length:
                self._text.text = self._text.text[:self._max_length]
            if self.upper:
                self.upper = False
            if self._keys[-1].hidden:
                self._keys[-1].hidden = False

    def backspace(self) -> None:
        text = self._text.text
        if len(text):
            text = text[:len(text)-1]
            if not len(text) and (self._column is None or self._row is None):
                self._keys[-1].hidden = True
            self._text.text = text

    def _handle_key(self, value:str) -> None:
        if value == "^":
            self.upper = not self.upper
        elif value == "<":
            self.backspace()
        elif value == ">":
            self.complete()
        else:
            self.append(value)

    def mousemove(self, x:int, y:int) -> None:
        for key in self._keys:
            contains = key.contains(x, y)
            key.hover = contains
            if contains:
                self._column, self._row = None, None  # reset position

    def mouseclick(self, x:int, y:int) -> None:
        for key in self._keys:
            if key.contains(x, y):
                self._handle_key(key.text)
                return True
            
    def _hover_selected(self) -> None:
        if self._column is not None and self._row is not None:
            # ensure that enter key is visible
            if self._keys[-1].hidden:
                self._keys[-1].hidden = False
            i = 0
            for y, row in enumerate(KEYBOARD_CHARS):
                for x in range(len(row)):
                    self._keys[i].hover = self._column == x and self._row == y
                    i += 1

    def _update_column(self, previous_row:int) -> None:
        self._column += (len(KEYBOARD_CHARS[self._row]) - len(KEYBOARD_CHARS[previous_row])) // 2  # fix offset
        self._column = min(max(self._column, 0), len(KEYBOARD_CHARS[self._row]))  # constrain to row
        
    def up(self) -> bool:
        if self._row is None or self._column is None:
            self._row = len(KEYBOARD_CHARS) - 1
            self._column = len(KEYBOARD_CHARS[self._row]) // 2
        else:
            previous_row = self._row
            self._row = (self._row - 1) % len(KEYBOARD_CHARS)
            self._update_column(previous_row)
        self._hover_selected()
        
    def down(self) -> bool:
        if self._row is None or self._column is None:
            self._row = 0
            self._column = len(KEYBOARD_CHARS[self._row]) // 2
        else:
            previous_row = self._row
            self._row = (self._row + 1) % len(KEYBOARD_CHARS)
            self._update_column(previous_row)
        self._hover_selected()
        
    def left(self, wrap:bool=True) -> bool:
        if self._row is None or self._column is None:
            self._row = len(KEYBOARD_CHARS) // 2 if wrap else len(KEYBOARD_CHARS) - 1
            self._column = len(KEYBOARD_CHARS[self._row]) - 1
        elif wrap:
            self._column = (self._column - 1) % len(KEYBOARD_CHARS[self._row])
        else:
            self._column -= 1
            if self._column < 0:
                self._row = (self._row - 1) % len(KEYBOARD_CHARS)
                self._column = len(KEYBOARD_CHARS[self._row]) - 1
        self._hover_selected()
        
    def right(self, wrap:bool=True) -> bool:
        if self._row is None or self._column is None:
            self._row = len(KEYBOARD_CHARS) // 2 if wrap else 0
            self._column = 0
        elif wrap:
            self._column = (self._column + 1) % len(KEYBOARD_CHARS[self._row])
        else:
            self._column += 1
            if self._column >= len(KEYBOARD_CHARS[self._row]):
                self._row = (self._row + 1) % len(KEYBOARD_CHARS)
                self._column = 0
        self._hover_selected()

    def select(self) -> bool:
        if self._column is not None and self._row is not None:
            i = 0
            for y, row in enumerate(KEYBOARD_CHARS):
                for x in range(len(row)):
                    if self._column == x and self._row == y:
                        self._handle_key(self._keys[i].text)
                        return True
                    i += 1
                    
    def stop(self) -> None:
        self._group.remove(self._keys)
        del self._keys
        self._group.remove(self._text)
        del self._text
        super().stop()
    
    def complete(self) -> None:
        if len(self._text.text):
            scene.player_name = self._text.text  # save name
            super().complete()

class Prompt(Entity):

    def __init__(self, text:str, options:list, margin:int=8, size:int=16, **kwargs):
        super().__init__(parent=graphics.overlay_group, **kwargs)
        
        self._tg = displayio.TileGrid(
            bitmap=graphics.fade_bmp, pixel_shader=graphics.fade_palette,
            width=graphics.display.width//graphics.FADE_TILE_SIZE, height=graphics.display.height//graphics.FADE_TILE_SIZE,
            tile_width=graphics.FADE_TILE_SIZE, tile_height=graphics.FADE_TILE_SIZE,
            default_tile=graphics.FADE_TILES//2,
        )
        self._group.append(self._tg)

        self._dialog = graphics.Dialog(text, force_width=True)
        self._dialog.y = graphics.display.height - margin*2 - size - self._dialog.height
        self._group.append(self._dialog)

        self._buttons = []
        width = self._dialog.width//len(options) - margin*(len(options) - 1)//len(options)
        for i, option in enumerate(options):
            button = graphics.Button(
                text=option,
                width=width, height=size,
                y=graphics.display.height - margin - size,
                x=self._dialog.x + (width + margin) * i,
            )
            self._buttons.append(button)
            self._group.append(button)

        self._index = None

    def play(self) -> None:
        global events
        super().play()
        # make sure we are front in the stack
        if self in events:
            events.remove(self)
        events.insert(0, self)

    def mousemove(self, x:int, y:int) -> None:
        for button in self._buttons:
            contains = button.contains(x, y)
            button.hover = contains
            if contains:
                self._index = None  # reset keyboard position
        return True  # always stop propagation

    def mouseclick(self, x:int, y:int) -> bool:
        for index, button in enumerate(self._buttons):
            if button.contains(x, y):
                self.select(index)
                break
        return True  # always stop propagation
    
    def up(self) -> bool:
        if self._index is None:
            self._index = len(self._buttons) - 1
        else:
            self._index = (self._index - 1) % len(self._buttons)
        for index, button in enumerate(self._buttons):
            button.hover = index == self._index

    def down(self) -> bool:
        if self._index is None:
            self._index = 0
        else:
            self._index = (self._index + 1) % len(self._buttons)
        for index, button in enumerate(self._buttons):
            button.hover = index == self._index

    def select(self, index:int = None) -> bool:
        if index is None and self._index is not None:
            index = self._index
        if index is not None and 0 <= index < len(self._buttons):
            self.complete(index)
        
    def complete(self, index:int = None) -> None:
        self.stop()
        if callable(self._on_complete):
            self._on_complete(index)

    def stop(self) -> None:
        self._group.remove(self._tg)
        del self._tg
        self._group.remove(self._dialog)
        del self._dialog
        for button in self._buttons:
            self._group.remove(button)
        del self._buttons
        super().stop()

exit_entity = None
class Exit(Entity):

    def __init__(self, margin:int=4):
        global exit_entity
        if exit_entity is not None:
            raise SystemError("An exit entity already exists")
        exit_entity = self
        
        super().__init__(parent=graphics.upper_group)
        bitmap, palette = adafruit_imageload.load("bitmaps/door.bmp")
        self._tg = displayio.TileGrid(
            bitmap=bitmap, pixel_shader=palette,
            y=margin, x=graphics.display.width-margin-bitmap.width//2,
            tile_width=bitmap.width//2, tile_height=bitmap.height,
        )
        self._tg.hidden = True
        self._group.append(self._tg)

    def update(self) -> None:
        if self._tg.hidden is True and graphics.cursor is not None:
            self._tg.hidden = False
        elif self._tg.hidden is False and graphics.cursor is None:
            self._tg.hidden = True

    def mousemove(self, x:int, y:int) -> None:
        self._tg[0, 0] = int(self._tg.contains((x, y, 0)))
        
    def mouseclick(self, x:int, y:int) -> bool:
        if self._tg.contains((x, y, 0)):
            self.complete()
            return True

    def select(self) -> bool:
        pass

    def complete(self, index:int=None) -> None:
        global events

        # Make sure we don't already have a prompt open
        if has_event(Prompt):
            return

        if index is None:
            Prompt(
                text="Are you sure you would like to return to the title screen and lose your current progress?",
                options=("Yes, please.", "No, keep playing!"),
                on_complete=self.complete,
            ).play()
        elif index == 0:
            super().complete()
                
            # stop background music
            sound.stop_music()
            
            # stop all events
            while events:
                events[-1].stop()
            if scene.current_scene is not None:
                scene.current_scene.stop()

            # reset level data
            scene.reset()
            
            # fade back to title screen
            Sequence(
                Fade(reverse=True, initial=graphics.FADE_TILES//2),
                lambda: scene.Title().start(),
            ).play()
        
    def stop(self) -> None:
        global exit_entity
        exit_entity = None
        self._group.remove(self._tg)
        del self._tg
        super().stop()
