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

class Level:

    def __init__(self, name:str):

        # load level data
        with open("content/{:s}.json".format(name), "r") as f:
            self._data = json.load(f)

        # load snake bitmap
        self._snake_bmp, snake_palette = adafruit_imageload.load("bitmaps/{:s}.bmp".format(name))
        snake_palette.make_transparent(self._data["bitmap_transparent"])
        self._snake_tg = displayio.TileGrid(self._snake_bmp, pixel_shader=snake_palette)

        self._dialog_index = -1
        self._dialog_voice = self._data.get("voice", 1)

    def start(self) -> None:
        engine.Sequence(
            engine.Fade(),
            lambda: graphics.lower_group.append(self._snake_tg),
            engine.Animator(target=self._snake_tg, start=(SNAKE_X, SNAKE_Y), end=(SNAKE_X, SNAKE_Y-self._snake_bmp.height)),
            lambda: self._next_dialog()
        ).play()

    def _next_dialog(self) -> None:
        self._dialog_index += 1
        if self._dialog_index >= len(self._data["dialogue"]):
            self.complete()
        else:
            self._do_dialog(self._data["dialogue"][self._dialog_index])

    def _do_dialog(self, item:str|list) -> None:
        if type(item) is str:
            engine.Dialog(item, voice=self._dialog_voice, on_complete=self._next_dialog).play()
        elif type(item) is list:
            # TODO: options & response
            pass

    def complete(self) -> None:
        engine.Sequence(
            engine.Animator(target=self._snake_tg, start=(SNAKE_X, SNAKE_Y-self._snake_bmp.height), end=(SNAKE_X, SNAKE_Y)),
            engine.Fade(reverse=True)
        ).play()

        graphics.lower_group.remove(self._snake_tg)
        del self._snake_tg
        del self._data
