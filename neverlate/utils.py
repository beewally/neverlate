from __future__ import annotations

import datetime
import os

from PySide6.QtGui import QIcon

from neverlate.constants import APP_NAME

# LOCAL_TIMEZONE = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo
LOCAL_TIMEZONE = datetime.datetime.now().astimezone().tzinfo
ICON_CACHE = {}  # type: dict[str, QIcon]


def app_local_data_dir() -> str:
    """
    Application data directory. Where we can safe preferences, tokens, etc.

    Returns:
        str: Folder path
    """
    if "HOME" in os.environ:
        # Linux/Mac
        folder = os.path.join(os.environ["HOME"], APP_NAME)
    else:
        # Windows
        folder = os.path.join(os.environ["APPDATA"], APP_NAME)

    if not os.path.exists(folder):
        os.makedirs(folder)
    return folder


def get_icon(name: str) -> QIcon:
    """Get an icon."""
    icon_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")
    if not name.endswith(".png"):
        name += ".png"
    icon = ICON_CACHE.get(name)
    if not icon:
        file_path = os.path.join(icon_dir, name)
        icon = QIcon(file_path)
        ICON_CACHE[name] = icon
    return icon


def now_datetime() -> datetime.datetime:
    """Current time in the users local time zone."""
    return datetime.datetime.now(LOCAL_TIMEZONE)


def pretty_datetime(dt: datetime.datetime) -> str:
    """Converts a date time to a a pretty syntax, e.g.: '4:33 PM'."""
    label = dt.strftime("%I:%M %p")
    if label[0] == "0":
        label = label[1:]
    return label
