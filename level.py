# SPDX-FileCopyrightText: 2025 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3
import displayio
import json

import adafruit_imageload

import engine
import graphics

SNAKE_X = 124
SNAKE_Y = 211

LEVELS = (
    "ozzie",
    "max",
    "ellis"
)

current_level = None
level_index = 0
level_scores = [0 for x in LEVELS]

class Level:

    def __init__(self, name:str=None):
        self._name = name if name is not None else LEVELS[0]

        # load level data
        with open("content/{:s}.json".format(self._name), "r") as f:
            self._data = json.load(f)

        # load snake bitmap
        self._snake_bmp, snake_palette = adafruit_imageload.load("bitmaps/{:s}.bmp".format(self._name))
        snake_palette.make_transparent(self._data["bitmap_transparent"])
        self._snake_tg = displayio.TileGrid(self._snake_bmp, pixel_shader=snake_palette)

        self._dialog_index = -1
        self._dialog_voice = self._data.get("voice", 1)

        self._score = 0

    @property
    def voice(self) -> int:
        return self._dialog_voice
    
    @property
    def title(self) -> str:
        return self._name[0].upper() + self._name[1:]

    @property
    def score(self) -> int:
        return self._score
    
    @score.setter
    def score(self, value: int) -> None:
        self._score = value

    def start(self) -> None:
        global current_level
        if current_level is not None:
            current_level.stop()
        current_level = self
        engine.Sequence(
            lambda: graphics.lower_group.append(self._snake_tg),
            engine.Animator(target=self._snake_tg, start=(SNAKE_X, SNAKE_Y), end=(SNAKE_X, SNAKE_Y-self._snake_bmp.height)),
            self._next_dialog
        ).play()

    def stop(self) -> None:
        global current_level
        if current_level is self:
            current_level = None

    def _next_dialog(self) -> None:
        self._dialog_index += 1
        if self._dialog_index >= len(self._data["dialogue"]):
            self.complete()
        else:
            self._do_dialog(self._data["dialogue"][self._dialog_index])

    def _do_dialog(self, item:str|list) -> None:
        if type(item) is str:
            engine.VoiceDialog(
                item, title=self.title, title_right=True,
                voice=self._dialog_voice, on_complete=self._next_dialog
            ).play()
        elif type(item) is list:
            engine.OptionDialog(item, on_complete=self._next_dialog).play()

    def complete(self) -> None:
        self.stop()
        engine.Sequence(
            engine.Animator(target=self._snake_tg, start=(SNAKE_X, SNAKE_Y-self._snake_bmp.height), end=(SNAKE_X, SNAKE_Y)),
            self._next_level
        ).play()

    def _next_level(self) -> None:
        graphics.lower_group.remove(self._snake_tg)
        del self._snake_tg
        del self._data

        global level_index, level_scores
        level_scores[level_index] = self.score
        level_index += 1
        if level_index < len(LEVELS):
            Level(LEVELS[level_index]).start()
        else:
            engine.Fade(reverse=True).play()
            # TODO: finish
