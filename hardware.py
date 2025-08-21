# SPDX-FileCopyrightText: 2025 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3
import array
import audiobusio
import audiomixer
import board
import time
import usb.core

import adafruit_tlv320
import adafruit_usb_host_descriptors

import config
import graphics

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
        dac.speaker_volume = -40
    else:
        # use headphones
        dac.headphone_output = True
        dac.headphone_volume = -15  # dB

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

mouse_interface_index, mouse_endpoint_address = None, None
mouse = None
mouse_was_attached = None

if "use_mouse" in config.launcher and config.launcher["use_mouse"]:

    # scan for connected USB device and loop over any found
    for device in usb.core.find(find_all=True):
        config_descriptor = adafruit_usb_host_descriptors.get_configuration_descriptor(device, 0)

        _possible_interface_index, _possible_endpoint_address = adafruit_usb_host_descriptors.find_boot_mouse_endpoint(device)
        if _possible_interface_index is not None and _possible_endpoint_address is not None:
            mouse = device
            mouse_interface_index = _possible_interface_index
            mouse_endpoint_address = _possible_endpoint_address

    mouse_was_attached = None
    if mouse is not None:
        # detach the kernel driver if needed
        if (mouse_was_attached := mouse.is_kernel_driver_active(0)):
            mouse.detach_kernel_driver(0)

        # set configuration on the mouse so we can use it
        mouse.set_configuration()
        mouse_buf = array.array("b", [0] * 8)

        # show cursor
        graphics.cursor_tg.hidden = False

def read_mouse() -> tuple|None:
    if mouse:
        try:
            count = mouse.read(mouse_endpoint_address, mouse_buf, timeout=20)
        except usb.core.USBTimeoutError:
            count = 0
        if count > 0:
            return (
                mouse_buf[1],              # x delta
                mouse_buf[2],              # y delta
                mouse_buf[0] & 0x01 != 0,  # left click
            )
