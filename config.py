# SPDX-FileCopyrightText: 2025 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3
import json

import adafruit_pathlib as pathlib

# global constants
TARGET_FRAME_RATE = 30
SAMPLE_RATE       = 11025
BIT_DEPTH         = 8

# read config
launcher = {}
if pathlib.Path("/launcher.conf.json").exists():
    with open("/launcher.conf.json", "r") as f:
        launcher = json.load(f)
