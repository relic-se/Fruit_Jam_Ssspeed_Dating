# SPDX-FileCopyrightText: 2025 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3
import audiocore
import os
import random

import adafruit_pathlib as pathlib

import hardware

DAC_PRESENT = hardware.peripherals.dac is not None

# load sfx wave files
SFX_CLICK = audiocore.WaveFile("sounds/click.wav") if DAC_PRESENT else None
SFX_BUZZER = audiocore.WaveFile("sounds/buzzer.wav") if DAC_PRESENT else None

# load voices
VOICE = {}
if DAC_PRESENT:
    for dir_path in (x for x in pathlib.Path("sounds").iterdir() if x.is_dir()):
        files = []
        for file_path in (x for x in dir_path.iterdir() if x.is_file()):
            if file_path.name.endswith(".wav"):
                files.append(audiocore.WaveFile(file_path.absolute()))
        if len(files):
            VOICE[dir_path.name] = files
        else:
            del files

def play_music(name:str="") -> None:
    if DAC_PRESENT:
        stop_music()
        path = pathlib.Path("sounds/music{:s}.wav".format("-" + name if len(name) else ""))
        if path.exists():
            hardware.mixer.play(audiocore.WaveFile(path.absolute()), voice=0, loop=True)

def stop_music() -> None:
    if DAC_PRESENT:
        hardware.mixer.voice[0].stop()

def play_sfx(wave:audiocore.WaveFile) -> None:
    if DAC_PRESENT and wave is not None:
        hardware.mixer.play(wave, voice=1, loop=False)

def play_voice(name:str) -> None:
    if DAC_PRESENT and len(name) and name in VOICE:
        wave = VOICE[name][random.randint(0, len(VOICE[name])-1)]
        if wave is not None:
            hardware.mixer.play(wave, voice=2, loop=False)

def is_voice_playing() -> bool:
    if DAC_PRESENT:
        return hardware.mixer.voice[2].playing
    return False
