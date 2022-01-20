"""Main app entry point."""
import ctypes
import os
import subprocess
import sys
import time
from pprint import pprint as pp
from typing import Any, Optional, Union

from PySide6.QtCore import Qt, QThread, QThreadPool, QTimer, Signal, Slot
from PySide6.QtGui import QAction, QCursor, QDesktopServices, QWindow
from PySide6.QtWidgets import (  # pylint: disable=no-name-in-module
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from calendar_alert.directories import get_icon


class PreferencesDialog(QDialog):  # pylint: disable=too-few-public-methods
    """Preferences dialog panes"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setWindowTitle("Preferences")
        self.setWindowIcon(get_icon("tray_icon.png"))
        self.quit_button = QPushButton("Press to quit")
        # self.button.clicked.connect(close_s)

        layout = QVBoxLayout()
        layout.addStretch()
        layout.addWidget(self.quit_button)
        self.setLayout(layout)
