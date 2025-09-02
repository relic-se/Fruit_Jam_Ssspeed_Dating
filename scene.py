# SPDX-FileCopyrightText: 2025 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3
import displayio
import json
import os

import adafruit_imageload

import engine
import graphics
import sound

SNAKE_X = 124
SNAKE_Y = 211

LEVELS = tuple([filename for filename in os.listdir("content") if filename.endswith(".json")])

current_scene = None
level_index = 0
level_scores = [0] * len(LEVELS)

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

class DialogueScene(Scene):

    def __init__(self, filename:str):
        super().__init__()

        # load data
        with open("content/{:s}".format(filename), "r") as f:
            self._data = json.load(f)

        # load snake bitmap
        self._snake_bmp, snake_palette = adafruit_imageload.load("bitmaps/{:s}.bmp".format(self._data["bitmap"]))
        snake_palette.make_transparent(self._data["bitmap_transparent"])
        self._snake_tg = displayio.TileGrid(self._snake_bmp, pixel_shader=snake_palette)

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
        graphics.lower_group.append(self._snake_tg)
        engine.Sequence(
            engine.Animator(target=self._snake_tg, start=(SNAKE_X, SNAKE_Y), end=(SNAKE_X, SNAKE_Y-self._snake_bmp.height)),
            self._next_dialog
        ).play()

    def _next_dialog(self) -> None:
        self._dialog_index += 1
        if self._dialog_index >= len(self._dialogue):
            self.complete()
        else:
            self._do_dialog(self._dialogue[self._dialog_index])

    def _do_dialog(self, item:str|list) -> None:
        if type(item) is str:
            engine.VoiceDialog(
                item, title=self.name, title_right=True,
                voice=True, on_complete=self._next_dialog
            ).play()
        elif type(item) is list:
            engine.OptionDialog(item, on_complete=self._next_dialog).play()
    
    def _next_scene(self) -> None:
        super()._next_scene()
        graphics.lower_group.remove(self._snake_tg)
        del self._snake_tg
        del self._data

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

    def complete(self) -> None:
        super().complete()
        engine.Sequence(
            engine.Animator(target=self._snake_tg, start=(SNAKE_X, SNAKE_Y-self._snake_bmp.height), end=(SNAKE_X, SNAKE_Y)),
            self._next_scene
        ).play()

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
        global level_scores, level_index
        super()._next_scene()

        # reset level and scores
        level_index = 0
        for i in range(len(level_scores)):
            level_scores[i] = 0

        # TODO: return to title
        Title().start()

class Title(Scene):

    def __init__(self):
        super().__init__()

    def start(self) -> None:
        super().start()
        engine.Sequence(
            engine.Title(),
            self.complete
        ).play()

    def complete(self) -> None:
        super().complete()
        engine.Sequence(
            engine.Fade(),
            self._next_scene
        ).play()

    def _next_scene(self) -> None:
        super()._next_scene()
        Level().start()
