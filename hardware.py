# SPDX-FileCopyrightText: 2025 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3
import audiobusio
import audiomixer
import board
import time

import adafruit_tlv320

import config

# Check if DAC is connected
i2c = board.I2C()
while not i2c.try_lock():
    time.sleep(0.01)
tlv320_present = 0x18 in i2c.scan()
i2c.unlock()

if tlv320_present:

    # setup audio
    dac = adafruit_tlv320.TLV320DAC3100(i2c)

    # set sample rate & bit depth
    dac.configure_clocks(
        sample_rate=config.SAMPLE_RATE,
        bit_depth=config.BIT_DEPTH,
    )

    if "sound" in config.launcher and config.launcher["sound"] == "speaker":
        dac.speaker_output = True
        dac.dac_volume = config.launcher["tlv320"].get("volume", 5)  # dB
    else:
        # use headphones
        dac.headphone_output = True
        dac.dac_volume = config.launcher["tlv320"].get("volume", 0) if "tlv320" in config.launcher else 0  # dB

    # setup audio output
    audio_config = {
        "buffer_size": 1024,
        "channel_count": 1,
        "sample_rate": config.SAMPLE_RATE,
        "bits_per_sample": config.BIT_DEPTH,
        "samples_signed": config.BIT_DEPTH >= 16,
    }
    audio = audiobusio.I2SOut(board.I2S_BCLK, board.I2S_WS, board.I2S_DIN)
    mixer = audiomixer.Mixer(voice_count=2, **audio_config)
    audio.play(mixer)

if "BUTTON1" in dir(board) and "BUTTON2" in dir(board) and "BUTTON3" in dir(board):
    from keypad import Keys
    buttons = Keys((board.BUTTON1, board.BUTTON2, board.BUTTON3), value_when_pressed=False, pull=True)
else:
    buttons = None
