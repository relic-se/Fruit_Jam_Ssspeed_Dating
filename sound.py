# SPDX-FileCopyrightText: 2025 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3
import audiocore

import hardware

if hardware.tlv320_present:

    # load wave files
    MUSIC = audiocore.WaveFile("sounds/music.wav")
    SFX_CLICK = audiocore.WaveFile("sounds/click.wav")

    # play wave file
    hardware.mixer.play(MUSIC, voice=0, loop=True)

else:
    SFX_CLICK = None

def play_sfx(wave:audiocore.WaveFile) -> None:
    if hardware.tlv320_present:
        hardware.mixer.play(wave, voice=1, loop=False)
