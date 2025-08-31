# SPDX-FileCopyrightText: 2025 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3
import json

import adafruit_pathlib as pathlib
from adafruit_simplemath import map_range

# global constants
TARGET_FRAME_RATE = 30
SAMPLE_RATE       = 11025
BIT_DEPTH         = 8

# read config
class LauncherConfig:

    def __init__(self):
        self._data = {}
        for directory in ("/", "/sd/", "/saves/"):
            launcher_config_path = directory + "launcher.conf.json"
            if pathlib.Path(launcher_config_path).exists():
                with open(launcher_config_path, "r") as f:
                    self._data = self._data | json.load(f)
        for key in ("palette", "audio"):
            if key not in self._data:
                self._data[key] = {}

    @property
    def data(self) -> dict:
        return self._data
    
    @data.setter
    def data(self, value: dict) -> None:
        self._data = value

    @property
    def use_mouse(self) -> bool:
        return "use_mouse" in self._data and self._data["use_mouse"]
    
    @use_mouse.setter
    def use_mouse(self, value: bool) -> None:
        self._data["use_mouse"] = value
        
    @property
    def favorites(self) -> list:
        return list(self._data["favorites"]) if "favorites" in self._data else []
    
    @favorites.setter
    def favorites(self, value: list) -> None:
        self._data["favorites"] = value
    
    @property
    def palette_bg(self) -> int:
        return int(self._data["palette"].get("bg", "0x222222"), 16)
    
    @palette_bg.setter
    def palette_bg(self, value: int) -> None:
        self._data["palette"]["bg"] = "0x{:06x}".format(value)
    
    @property
    def palette_fg(self) -> int:
        return int(self._data["palette"].get("fg", "0xffffff"), 16)
    
    @palette_fg.setter
    def palette_fg(self, value: int) -> None:
        self._data["palette"]["fg"] = "0x{:06x}".format(value)
    
    @property
    def palette_arrow(self) -> int:
        return int(self._data["palette"].get("arrow", "0x004abe"), 16)
    
    @palette_arrow.setter
    def palette_arrow(self, value: int) -> None:
        self._data["palette"]["arrow"] = "0x{:06x}".format(value)
    
    @property
    def palette_accent(self) -> int:
        return int(self._data["palette"].get("accent", "0x008800"), 16)
    
    @palette_accent.setter
    def palette_accent(self, value: int) -> None:
        self._data["palette"]["accent"] = "0x{:06x}".format(value)
    
    @property
    def audio_output(self) -> str:
        return self._data["audio"].get("output")
    
    @audio_output.setter
    def audio_output(self, value: str) -> None:
        self._data["audio"]["output"] = value
    
    @property
    def audio_output_speaker(self) -> bool:
        return self.audio_output == "speaker"
    
    @property
    def audio_output_headphones(self) -> bool:
        return not self.audio_output_speaker
    
    @property
    def audio_volume(self) -> int:
        return min(max(int(self._data["audio"].get("volume", 12)), 1), 20)
    
    @audio_volume.setter
    def audio_volume(self, value: int) -> None:
        self._data["audio"]["volume"] = min(max(value, 1), 20)

    @property
    def audio_volume_db(self) -> int:
        return map_range(self.audio_volume, 1, 20, -63, 23)

    @property
    def boot_animation(self) -> str:
        value = self._data["boot_animation"] if "boot_animation" in self._data else ""
        if not value.endswith(".py") or not pathlib.Path(value).exists():
            return "/boot_animation.py"
        return value
    
    @boot_animation.setter
    def boot_animation(self, value: str) -> None:
        if value.endswith(".py") and pathlib.Path(value).exists():
            self._data["boot_animation"] = value

    def save(self) -> None:
        with open("/saves/launcher.conf.json", "w") as f:
            json.dump(self._data, f)

    def __str__(self) -> str:
        return str(self._data)

launcher = LauncherConfig()
