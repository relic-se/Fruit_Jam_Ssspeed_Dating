# SPDX-FileCopyrightText: 2025 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3
import audiocore
import random

import hardware

if hardware.tlv320_present:

    # load wave files
    MUSIC = audiocore.WaveFile("sounds/music.wav")
    SFX_CLICK = audiocore.WaveFile("sounds/click.wav")

    # play wave file
    hardware.mixer.play(MUSIC, voice=0, loop=True)

    VOICE = tuple([
        tuple([
            audiocore.WaveFile("sounds/voice{:d}_{:d}.wav".format(i+1, j))
            for j in range(6)
        ]) for i in range(2)
    ])

else:
    SFX_CLICK = None
    VOICE = tuple([(None,) for i in range(2)])

def play_sfx(wave:audiocore.WaveFile) -> None:
    if hardware.tlv320_present and wave is not None:
        hardware.mixer.play(wave, voice=1, loop=False)

def play_voice(voice:int=1) -> None:
    if hardware.tlv320_present and voice > 0:
        voice = (voice-1) % len(VOICE)
        wave = VOICE[voice][random.randint(0, len(VOICE[voice])-1)]
        if wave is not None:
            hardware.mixer.play(wave, voice=2, loop=False)

def is_voice_playing() -> bool:
    if hardware.tlv320_present:
        return hardware.mixer.voice[2].playing
    return False
