# SPDX-FileCopyrightText: 2025 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3
import audiocore
import os
import random

import adafruit_pathlib as pathlib

import hardware

VOICE = None

# load sfx wave files
SFX_CLICK = audiocore.WaveFile("sounds/click.wav") if hardware.tlv320_present else None
SFX_BUZZER = audiocore.WaveFile("sounds/buzzer.wav") if hardware.tlv320_present else None

def play_music(name:str="") -> None:
    if hardware.tlv320_present:
        stop_music()
        path = pathlib.Path("sounds/music{:s}.wav".format("-" + name if len(name) else ""))
        if path.exists():
            hardware.mixer.play(audiocore.WaveFile(path.absolute()), voice=0, loop=True)

def stop_music() -> None:
    if hardware.tlv320_present:
        hardware.mixer.voice[0].stop()

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
    if hardware.tlv320_present:
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
    if hardware.tlv320_present:
        hardware.mixer.voice[2].stop()
        if VOICE is not None:
            del VOICE
            VOICE = None

def is_voice_playing() -> bool:
    if hardware.tlv320_present:
        return hardware.mixer.voice[2].playing
    return False
