# SPDX-FileCopyrightText: 2025 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3
import audiomixer

import adafruit_fruitjam

try:
    import launcher_config
    config = launcher_config.LauncherConfig()
except ImportError:
    config = None

peripherals = adafruit_fruitjam.peripherals.Peripherals(
    sample_rate=11025,
    bit_depth=8,
)

if config is not None:
    peripherals.audio_output = config.audio_output
    peripherals.volume = config.audio_volume
else:
    peripherals.audio_output = "headphone"
    peripherals.volume = 12

if peripherals.dac is not None:
    peripherals.dac.headphone_volume = -15  # line level

    # setup audio mixer
    mixer = audiomixer.Mixer(
        voice_count=3,
        buffer_size=1024,
        channel_count=1,
        sample_rate=peripherals.dac.sample_rate,
        bits_per_sample=peripherals.dac.bit_depth,
        samples_signed=peripherals.dac.bit_depth >= 16,
    )
    peripherals.audio.play(mixer)
