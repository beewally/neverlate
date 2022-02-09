"""Main app entry point."""
from __future__ import annotations

import json
import os
from typing import Any, ClassVar

from neverlate.utils import app_local_data_dir


class _Preferences:

    _pref_file_path: ClassVar[str] = os.path.join(
        app_local_data_dir(), "preferences.json"
    )

    alert_padding: int  # Minutes before an event that an alert should be displayed
    calendar_visibility: dict[str, bool]  # Wether the calendar is enabled or not
    download_cal_freq: int  # Frequency in minutes that the calendar + events are downloaded

    def __init__(self) -> None:
        self.alert_padding = 5
        self.calendar_visibility = {}  # ty
        self.download_cal_freq = 5

    def deserialize(self, **kwargs: Any):
        """Load preferences from a dictionary."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def load(self):
        """Load preferences from disk."""
        if not os.path.exists(self._pref_file_path):
            return
        try:
            with open(self._pref_file_path, "r") as pref_file:
                data = json.load(pref_file)
        except:
            print("WARNING: unable to load prefernces!")
            data = {}
        self.deserialize(**data)

    def save(self):
        """Save the preferences to disk."""
        data = self.serialize()
        with open(self._pref_file_path, "w") as pref_file:
            json.dump(data, pref_file, sort_keys=True, indent=4)

    def serialize(self) -> dict[str, Any]:
        """Save preferences to a dictionary."""
        return {
            "alert_padding": self.alert_padding,
            "calendar_visibility": self.calendar_visibility,
            "download_cal_freq": self.download_cal_freq,
        }


PREFERENCES = _Preferences()
PREFERENCES.load()
