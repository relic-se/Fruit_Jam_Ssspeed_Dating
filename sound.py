# SPDX-FileCopyrightText: 2025 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3
import audiocore
import os
import random

import adafruit_pathlib as pathlib

import hardware

VOICE = None

if hardware.tlv320_present:

    # load wave files
    MUSIC = audiocore.WaveFile("sounds/music.wav")
    SFX_CLICK = audiocore.WaveFile("sounds/click.wav")
    SFX_BUZZER = audiocore.WaveFile("sounds/buzzer.wav")

    # play wave file
    hardware.mixer.play(MUSIC, voice=0, loop=True)

else:
    MUSIC = None
    SFX_CLICK = None
    SFX_BUZZER = None

def play_sfx(wave:audiocore.WaveFile) -> None:
    if hardware.tlv320_present and wave is not None:
        hardware.mixer.play(wave, voice=1, loop=False)

def play_voice() -> None:
    if hardware.tlv320_present and VOICE is not None:
        wave = VOICE[random.randint(0, len(VOICE)-1)]
        if wave is not None:
            hardware.mixer.play(wave, voice=2, loop=False)

def load_voice(name:str) -> None:
    global VOICE
    unload_voice()
    if len(name):
        path = pathlib.Path("sounds/{:s}".format(name))
        if path.exists():
            VOICE = []
            for filename in os.listdir(path.absolute()):
                if filename.endswith(".wav"):
                    VOICE.append(audiocore.WaveFile((path / filename).absolute()))
            if not len(VOICE):
                unload_voice()

def unload_voice() -> None:
    global VOICE
    hardware.mixer.voice[2].stop()
    if VOICE is not None:
        del VOICE
        VOICE = None

def is_voice_playing() -> bool:
    if hardware.tlv320_present:
        return hardware.mixer.voice[2].playing
    return False
