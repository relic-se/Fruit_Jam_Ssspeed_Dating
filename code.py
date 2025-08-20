# SPDX-FileCopyrightText: 2025 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3
import array
import audiobusio
import audiocore
import audiomixer
import board
import displayio
import fontio
import json
import math
import sys
import supervisor
from terminalio import FONT
import time
import usb.core

from adafruit_display_text.text_box import TextBox
from adafruit_fruitjam.peripherals import request_display_config
import adafruit_imageload
import adafruit_pathlib as pathlib
import adafruit_tlv320
import adafruit_usb_host_descriptors
from font_knewave_outline_webfont_18 import FONT as FONT_TITLE

TEXT_SPEED = 0.1
BOB_SPEED = 0.2
WINDOW_REVEAL_DURATION = 1.0

# setup display
request_display_config(320, 240)
display = supervisor.runtime.display
display.auto_refresh = False

# create root group
main_group = displayio.Group()
display.root_group = main_group
display.refresh()  # blank out screen

# create group for game elements
scene_group = displayio.Group()
main_group.append(scene_group)

# read config
launcher_config = {}
if pathlib.Path("launcher.conf.json").exists():
    with open("launcher.conf.json", "r") as f:
        launcher_config = json.load(f)

# Check if DAC is connected
i2c = board.I2C()
while not i2c.try_lock():
    time.sleep(0.01)
tlv320_present = 0x18 in i2c.scan()
i2c.unlock()

if tlv320_present:
    # setup audio
    dac = adafruit_tlv320.TLV320DAC3100(i2c)

    # load wave files
    music = audiocore.WaveFile("sounds/music.wav")
    sfx_click = audiocore.WaveFile("sounds/click.wav")

    # set sample rate & bit depth
    dac.configure_clocks(
        sample_rate=music.sample_rate,
        bit_depth=music.bits_per_sample,
    )

    if "sound" in launcher_config and launcher_config["sound"] == "speaker":
        dac.speaker_output = True
        dac.speaker_volume = -40
    else:
        # use headphones
        dac.headphone_output = True
        dac.headphone_volume = -15  # dB

    # setup audio output
    audio_config = {
        "buffer_size": 1024,
        "channel_count": music.channel_count,
        "sample_rate": music.sample_rate,
        "bits_per_sample": music.bits_per_sample,
        "samples_signed": music.bits_per_sample >= 16,
    }
    audio = audiobusio.I2SOut(board.I2S_BCLK, board.I2S_WS, board.I2S_DIN)
    mixer = audiomixer.Mixer(voice_count=2, **audio_config)
    audio.play(mixer)

    # play wave file
    mixer.play(music, voice=0, loop=True)

else:
    sfx_click = None

def play_sfx(wave:audiocore.WaveFile) -> None:
    if tlv320_present:
        mixer.play(wave, voice=1, loop=False)

# load the mouse cursor bitmap
cursor_bmp, cursor_palette = adafruit_imageload.load("bitmaps/cursor.bmp")
cursor_palette.make_transparent(0)

# create a TileGrid for the mouse, using its bitmap and pixel_shader
cursor_tg = displayio.TileGrid(
    bitmap=cursor_bmp, pixel_shader=cursor_palette,
    x=display.width//2, y=display.height//2,
)

mouse_interface_index, mouse_endpoint_address = None, None
mouse = None
mouse_was_attached = None

if "use_mouse" in launcher_config and launcher_config["use_mouse"]:

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
        main_group.append(cursor_tg)

# add background image
bg_bmp, bg_palette = adafruit_imageload.load("bitmaps/bg.bmp")
bg_tg = displayio.TileGrid(bg_bmp, pixel_shader=bg_palette)
scene_group.append(bg_tg)

# add blinka
snake_bmp, snake_palette = adafruit_imageload.load("bitmaps/snake.bmp")
snake_palette.make_transparent(4)
snake_tg = displayio.TileGrid(snake_bmp, pixel_shader=snake_palette,
                              x=124, y=25)
scene_group.append(snake_tg)

# add table image
table_bmp, table_palette = adafruit_imageload.load("bitmaps/table.bmp")
table_palette.make_transparent(3)
table_tg = displayio.TileGrid(table_bmp, pixel_shader=table_palette,
                              y=display.height-table_bmp.height)  # move to bottom of display
scene_group.append(table_tg)

# load window image
window_bmp, window_palette = adafruit_imageload.load("bitmaps/window.bmp")
window_palette.make_transparent(1)
WINDOW_TILE_SIZE = 8

class TextWindow(displayio.Group):

    def __init__(self, width:int, height:int, text:str="", font:fontio.FontProtocol=FONT, **kwargs):
        super().__init__(**kwargs)
        width = math.ceil(width / WINDOW_TILE_SIZE)
        height = math.ceil(height / WINDOW_TILE_SIZE)
        if width < 3 or height < 3:
            raise ValueError("Width and/or height are too small!")
        
        # setup window background grid
        self._tg = displayio.TileGrid(
            bitmap=window_bmp, pixel_shader=window_palette,
            width=width, height=height,
            tile_width=WINDOW_TILE_SIZE, tile_height=WINDOW_TILE_SIZE, default_tile=4,
        )
        self.append(self._tg)

        # set corners
        self._tg[0, 0] = 0
        self._tg[self._tg.width-1, 0] = 2
        self._tg[0, self._tg.height-1] = 6
        self._tg[self._tg.width-1, self._tg.height-1] = 8

        # set borders
        for x in range(1, self._tg.width-1):
            self._tg[x, 0] = 1
            self._tg[x, self._tg.height-1] = 7
        for y in range(1, self._tg.height-1):
            self._tg[0, y] = 3
            self._tg[self._tg.width-1, y] = 5

        # setup textbox
        try:
            bb_width, bb_height, bb_x_offset, bb_y_offset = font.get_bounding_box()
        except ValueError:
            bb_width, bb_height = font.get_bounding_box()
            bb_x_offset, bb_y_offset = 0, 0
        self._tb = TextBox(
            font=font,
            width=self.width-14, height=self.height,
            x=7, y=5+((bb_height+bb_y_offset)//2),
        )
        self.append(self._tb)

        self._text = text
        self._text_index = 0
        self._text_delta = 0.0

    @property
    def width(self) -> int:
        return self._tg.width * WINDOW_TILE_SIZE
        
    @property
    def height(self) -> int:
        return self._tg.height * WINDOW_TILE_SIZE
    
    @property
    def text(self) -> str:
        return self._tb.text
    
    @text.setter
    def text(self, value:str) -> None:
        self._tb.text = ""
        self._text = value
        self._text_index = 0
        self._text_delta = 0.0

    def update(self, delta:float) -> None:
        if self._text_index < len(self._text):
            self._text_delta += delta
            while self._text_delta >= TEXT_SPEED and self._text_index < len(self._text):
                while self._text_index < len(self._text):
                    ch = self._text[self._text_index]
                    self._tb.text += ch
                    self._text_index += 1
                    if ch not in (" ", "\n", "\t"):
                        break
                self._text_delta -= TEXT_SPEED

text_window = TextWindow(
    width=256, height=56,
    text="Hello, World! My name is Blinka, and I'm a snake. What would you like to ask me about?",
)
text_window.x = (display.width - text_window.width) // 2
text_window.y = (display.height - text_window.height) - 16
scene_group.append(text_window)

class Animator:
    def __init__(self, target:displayio.Group, end:tuple, duration:float, start:tuple=None):
        self._target = target
        self._end = end
        self._duration = duration
        self._accumulator = 0.0

        if start is not None:
            self._assign(start)
        self._start = (self._target.x, self._target.y)

    def _assign(self, value:tuple) -> None:
        self._target.x, self._target.y = value

    @property
    def animating(self) -> bool:
        return self._accumulator < self._duration

    def update(self, delta:float) -> None:
        self._accumulator += delta
        if self.animating:
            pos = min(self._accumulator / self._duration, 1.0)
            self._assign((
                int((self._end[0] - self._start[0]) * pos + self._start[0]),
                int((self._end[1] - self._start[1]) * pos + self._start[1]),
            ))

    def reverse(self) -> None:
        self._start, self._end = self._end, self._start
        self.reset()

    def reset(self) -> None:
        self._accumulator = 0.0

text_window_animation = Animator(
    target=text_window, duration=WINDOW_REVEAL_DURATION,
    start=(text_window.x, display.height),
    end=(text_window.x, (display.height - text_window.height) - 16),
)

# initial display refresh
display.refresh()

current_timestamp = time.monotonic()
previous_timestamp = 0
while True:

    # handle keyboard input
    while (c := supervisor.runtime.serial_bytes_available) > 0:
        key = sys.stdin.read(c)

        # up key
        if key == "\x1b[A":
            pass

        # down key
        elif key == "\x1b[B":
            pass

        # enter
        elif key == "\n":
            if not text_window_animation.animating:
                text_window_animation.reverse()

    # handle mouse input
    if mouse:
        try:
            count = mouse.read(mouse_endpoint_address, mouse_buf, timeout=20)
        except usb.core.USBTimeoutError:
            count = 0
        if count > 0:
            cursor_tg.x = min(max(cursor_tg.x + mouse_buf[1], 0), display.width - 1)
            cursor_tg.y = min(max(cursor_tg.y + mouse_buf[2], 0), display.height - 1)
            if mouse_buf[0] & 0x01 != 0:  # left click
                play_sfx(sfx_click)
    
    # update time delta
    previous_timestamp = current_timestamp
    current_timestamp = time.monotonic()
    delta = current_timestamp - previous_timestamp

    # snake bob animation (mostly just for testing)
    #snake_tg.y = int(math.sin(current_timestamp * math.pi * BOB_SPEED) * 5 + 25)

    # write out window text and animate window reveal
    text_window.update(delta)
    text_window_animation.update(delta)

    # update display if any changes were made
    display.refresh()
