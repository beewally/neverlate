import datetime
import os
import sys
import time
from pprint import pprint as pp
from typing import Any

from PySide6.QtCore import QObject
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QDialog, QMenu, QSystemTrayIcon

from calendar_alert.directories import get_icon, icon_dir
from google_cal_downloader import GoogleCalDownloader


class PreferencesDialog(QDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle("Preferences")


class App:
    def __init__(self):
        # Create a Qt application
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.preferences_dialog = PreferencesDialog()
        self.tray = QSystemTrayIcon()
        self._setup_tray()

        # Log in & get google calendar events
        self.google_cal = GoogleCalDownloader()
        self.events = self.google_cal.get_events()

    def _setup_tray(self):

        menu = QMenu()
        settingAction = menu.addAction("Preferences")
        settingAction.triggered.connect(self.preferences_dialog.show)
        exitAction = menu.addAction("Quit")
        exitAction.triggered.connect(sys.exit)
        self.tray.setIcon(get_icon("tray_icon.png"))
        self.tray.setContextMenu(menu)
        self.tray.show()
        self.tray.setToolTip("Bwalters was here!")
        self.tray.showMessage(
            "My Great Title",
            "You're late for an event!",
            get_icon("tray_icon.png"),
        )
        # self.tray.showMessage("fuga", "moge")

    def run(self):
        # Enter Qt application main loop
        self.app.exec()
        sys.exit()


if __name__ == "__main__":
    app = App()
    app.run()
