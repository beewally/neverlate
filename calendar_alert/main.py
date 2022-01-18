"""Main app entry point."""
import sys
import time
from calendar import calendar
from pprint import pprint as pp
from typing import Any

from PySide6.QtCore import QThread, QThreadPool, QTimer, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (  # pylint: disable=no-name-in-module
    QApplication,
    QDialog,
    QMenu,
    QPushButton,
    QSystemTrayIcon,
    QVBoxLayout,
)

from calendar_alert.directories import get_icon
from calendar_alert.google_cal_downloader import GoogleCalDownloader


class UpdateCalendar(QThread):
    def __init__(self, calendar: GoogleCalDownloader) -> None:
        super().__init__()
        self.calendar = calendar

    def run(self):
        print("WORKER THREAD IS WORKING")
        self.calendar.update_calendars()
        self.calendar.update_events()


class PreferencesDialog(QDialog):  # pylint: disable=too-few-public-methods
    """Preferences dialog panes"""

    close_signal = Signal()

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


class App:
    """Main calendar_alert Qt application."""

    tray: QSystemTrayIcon

    def __init__(self) -> None:
        # Create a Qt application
        self.app = QApplication(sys.argv)
        self.app.aboutToQuit.connect(self.quitting)
        self.app.setQuitOnLastWindowClosed(False)
        # self.app.setWindowIcon(get_icon("tray_icon.png"))  # DOesn't seem to work
        self.preferences_dialog = PreferencesDialog()
        self.preferences_dialog.quit_button.clicked.connect(self.app.quit)
        self._setup_tray()

        # Log in & get google calendar events
        self.gcal = GoogleCalDownloader()

        self.calendars = self.gcal.update_calendars()

        # Timer - runs in the main thread every 1 second
        self.my_timer = QTimer()
        self.my_timer.timeout.connect(self.update)
        self.my_timer.start(0.5 * 1000)  # 1 sec intervall

        self.update_calendar_thread = UpdateCalendar(self.gcal)
        self.update_calendar_thread.finished.connect(self.bg_update_thread_finished)
        self.update_calendar_thread.start()

    def bg_update_thread_finished(self):
        print("PRINT WORKER() - DONE?!")
        self.preferences_dialog.quit_button.setText(
            f"All done: {len(self.gcal.events)}"
        )
        # self.my_worker.start()

        # time.sleep(0.8)

    def _setup_tray(self) -> None:

        menu = QMenu()
        settingAction = menu.addAction("Preferences")
        settingAction.triggered.connect(self.preferences_dialog.show)
        exitAction = menu.addAction("Quit")
        exitAction.triggered.connect(self.app.exit)
        self.tray = QSystemTrayIcon()
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

    def quitting(self) -> None:
        print("QUITTING")
        self.update_calendar_thread.finished.disconnect()
        self.update_calendar_thread.terminate()
        # self.thread.wait()

    def run(self):
        self.preferences_dialog.show()
        # Enter Qt application main loop
        self.app.exec()
        sys.exit()

    def update(self):
        print("UPDATE:", self.update_calendar_thread.isFinished())
        if self.update_calendar_thread.isFinished():
            self.update_calendar_thread.start()
            self.preferences_dialog.quit_button.setText("Reset")
        pass


if __name__ == "__main__":
    app = App()
    app.run()
