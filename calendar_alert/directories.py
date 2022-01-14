import os

from PySide6.QtGui import QIcon

ICON_CACHE = {}


def app_data_dir() -> str:
    """
    Application data directory.

    Returns:
        str: Folder path
    """
    folder_name = "calendar_alert"
    if "HOME" in os.environ:
        # Linux/Mac
        folder = os.path.join(os.environ["HOME"], folder_name)
    else:
        # Windows
        folder = os.path.join(os.environ["APPDATA"], folder_name)

    if not os.path.exists(folder):
        os.makedirs(folder)
    return folder


def get_icon(name: str) -> QIcon:
    if not name.endswith(".png"):
        name += ".png"
    icon = ICON_CACHE.get(name)
    if not icon:
        fp = os.path.join(icon_dir(), name)
        icon = QIcon(fp)
        ICON_CACHE[name] = icon
    return icon


def icon_dir() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")
