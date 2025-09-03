# SPDX-FileCopyrightText: 2025 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3
import displayio
import json
import os
import re

import adafruit_imageload

import engine
import graphics
import sound

SNAKE_X = 124
SNAKE_Y = 211

level_regex = re.compile("^\d\d-[\w-]+\.json$")
LEVELS = tuple(sorted([filename for filename in os.listdir("content") if level_regex.match(filename)]))

current_scene = None
level_index = 0
level_scores = [0] * len(LEVELS)

player_name = ""

class Scene:

    def __init__(self):
        pass

    def start(self) -> None:
        global current_scene
        if current_scene is not None:
            current_scene.stop()
        current_scene = self

    def stop(self) -> None:
        global current_scene
        if current_scene is self:
            current_scene = None

    def complete(self) -> None:
        self.stop()

    def _next_scene(self) -> None:
        pass

class Title(Scene):

    def __init__(self):
        super().__init__()

    def start(self) -> None:
        super().start()
        sound.stop_music()
        engine.Sequence(
            engine.Title(),
            self.complete
        ).play()

    def complete(self) -> None:
        super().complete()
        sound.play_music()
        engine.Sequence(
            engine.Fade(),
            self._next_scene
        ).play()

    def _next_scene(self) -> None:
        super()._next_scene()
        Intro().start()

class DialogueScene(Scene):

    def __init__(self, filename:str):
        super().__init__()

        # load data
        with open("content/" + filename, "r") as f:
            self._data = json.load(f)

        # load character bitmap
        if "bitmap" in self._data:
            self._bitmap, palette = adafruit_imageload.load("bitmaps/{:s}.bmp".format(self._data["bitmap"]))
            if "bitmap_transparent" in self._data:
                palette.make_transparent(int(self._data.get("bitmap_transparent")))
            self._tg = displayio.TileGrid(self._bitmap, pixel_shader=palette)
        else:
            self._tg = None

        # load voice
        sound.load_voice(self._data.get("voice", ""))

        # configure dialogue
        self._dialog_index = -1
        self._dialogue = self._get_dialogue()

    def _get_dialogue(self) -> list:
        raise NotImplementedError()
    
    @property
    def name(self) -> str:
        return self._data["name"]

    def start(self) -> None:
        super().start()
        graphics.lower_group.append(self._tg)
        engine.Sequence(
            engine.Animator(target=self._tg, start=(SNAKE_X, SNAKE_Y), end=(SNAKE_X, SNAKE_Y-self._bitmap.height)),
            self._next_dialog
        ).play()

    def _next_dialog(self) -> None:
        self._dialog_index += 1
        if self._dialog_index >= len(self._dialogue):
            self.complete()
        else:
            self._do_dialog(self._dialogue[self._dialog_index])

    def _do_dialog(self, item:str|list, shuffle:bool=True) -> None:
        if type(item) is str:
            engine.VoiceDialog(
                item, title=self.name, title_right=True,
                voice=True, on_complete=self._next_dialog
            ).play()
        elif type(item) is list:
            engine.OptionDialog(item, shuffle=shuffle, on_complete=self._next_dialog).play()

    def complete(self) -> None:
        super().complete()
        engine.Sequence(
            engine.Animator(target=self._tg, start=(SNAKE_X, SNAKE_Y-self._bitmap.height), end=(SNAKE_X, SNAKE_Y)),
            self._next_scene
        ).play()
    
    def _next_scene(self) -> None:
        super()._next_scene()
        graphics.lower_group.remove(self._tg)
        del self._tg
        del self._bitmap
        del self._data

class Intro(DialogueScene):

    def __init__(self):
        super().__init__("intro.json")

    def _get_dialogue(self) -> list:
        return self._data["dialogue"]

    def _do_dialog(self, item:str|list) -> None:
        if type(item) is str and item == "[enter_name]":
            engine.Keyboard(on_complete=self._next_dialog).play()
        else:
            super()._do_dialog(item, shuffle=False)

    def _next_scene(self) -> None:
        super()._next_scene()
        Level().start()

class Level(DialogueScene):

    def __init__(self, filename:str=None):
        super().__init__(filename if filename is not None else LEVELS[0])
        self._score = 0

    def _get_dialogue(self) -> list:
        return self._data["dialogue"]

    @property
    def score(self) -> int:
        return self._score
    
    @score.setter
    def score(self, value: int) -> None:
        self._score = value

    def _next_scene(self) -> None:
        global level_index, level_scores
        super()._next_scene()

        level_scores[level_index] = self.score
        level_index += 1
        if level_index < len(LEVELS):
            Level(LEVELS[level_index]).start()
        else:
            Epilogue().start()

class Epilogue(DialogueScene):

    def __init__(self):
        # determine the highest scoring level
        name = LEVELS[level_scores.index(max(level_scores))]
        super().__init__(name)
        self._results = False

    def _get_dialogue(self) -> list:
        return self._data["epilogue"]
    
    def start(self) -> None:
        sound.play_music("epilogue")
        super().start()
    
    def complete(self) -> None:
        if not self._results:
            self._results = True
            engine.Sequence(
                engine.Results(),
                self.complete
            ).play()
        else:
            super().complete()
            engine.Sequence(
                engine.Fade(reverse=True),
                self._next_scene
            ).play()

    def _next_scene(self) -> None:
        global level_scores, level_index, player_name
        super()._next_scene()

        # reset level and scores
        level_index = 0
        for i in range(len(level_scores)):
            level_scores[i] = 0
        player_name = ""

        # TODO: return to title
        Title().start()
