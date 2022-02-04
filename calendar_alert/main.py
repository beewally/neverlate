"""Main app entry point."""
from __future__ import annotations

import ctypes
import sys
import time

from google.auth.exceptions import RefreshError
from PySide6.QtCore import QRect  # pylint: disable=no-name-in-module
from PySide6.QtCore import Qt  # pylint: disable=no-name-in-module
from PySide6.QtCore import QThread, QTimer, Slot
from PySide6.QtWidgets import (  # pylint: disable=no-name-in-module
    QApplication,
    QMenu,
    QSystemTrayIcon,
)

from calendar_alert.constants import APP_NAME
from calendar_alert.event_alerter import EventAlerter
from calendar_alert.google_cal_downloader import GoogleCalDownloader
from calendar_alert.main_dialog import MainDialog
from calendar_alert.preferences import PreferencesDialog
from calendar_alert.utils import get_icon

# TODO: add a column for attending status, join button, reset time alert button
# TODO: support calendars
# TODO: support preferences

MINUTES_BEFORE_ALERT = 10  # TODO: make this a preference


class UpdateCalendar(QThread):
    def __init__(self, calendar: GoogleCalDownloader) -> None:
        super().__init__()
        self.calendar = calendar

    def run(self):
        try:
            self.calendar.update_calendars()
            self.calendar.update_events()
        except RefreshError:
            print("BAD THINGS HAVE HAPPENED AND NEED TO BE FIXED")
            raise


class App:
    """Main Qt application."""

    UPDATE_FREQUENCY = 60  # seconds to wait before downloading new events

    tray: QSystemTrayIcon

    def __init__(self) -> None:
        # Create a Qt application
        self.app = QApplication(sys.argv)
        self.app.aboutToQuit.connect(self.quitting)
        self.app.setQuitOnLastWindowClosed(False)
        self.main_dialog = MainDialog()
        self.main_dialog.quit_button.clicked.connect(self.app.quit)
        self.main_dialog.update_now_button.clicked.connect(self.on_update_now)

        # Size of initial window
        rect = QRect(0, 0, 600, 300)
        screen_geo = self.app.primaryScreen().geometry()
        rect.moveCenter(screen_geo.center())
        self.main_dialog.setGeometry(rect)

        self.preferences_dialog = PreferencesDialog()
        self._setup_tray()

        # Log in & get google calendar events
        self.gcal = GoogleCalDownloader()
        self.gcal.update_calendars()

        # Timer - runs in the main thread every 1 second
        self.my_timer = QTimer()
        self.my_timer.timeout.connect(self.update)
        self.my_timer.start(1 * 1000)  # 1 sec intervall

        self.update_calendar_thread = UpdateCalendar(self.gcal)
        self.update_calendar_thread.finished.connect(
            self.thread_download_calendar_finished
        )
        self.update_calendar_thread.started.connect(
            self.thread_download_calendar_started
        )
        self.update_calendar_thread.start()

        self.event_alerters = {}  # type: dict[str, EventAlerter]

    def _setup_tray(self) -> None:
        menu = QMenu()
        settingAction = menu.addAction("Preferences")
        settingAction.triggered.connect(self.preferences_dialog.show)
        exitAction = menu.addAction("Quit")
        exitAction.triggered.connect(self.app.exit)
        self.tray = QSystemTrayIcon()
        self.tray.activated.connect(self.tray_clicked)
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

    def close_all_pop_ups(self):

        for event in self.event_alerters.values():
            event._alerter.close_pop_ups()

    def on_update_now(self):
        """User manually requested the calanders be re-downloaded."""
        self.update_calendar_thread.start()
        self.update()

    def quitting(self) -> None:
        """Quitting the app. Make sure we terminate all threads first."""
        self.update_calendar_thread.finished.disconnect()
        self.update_calendar_thread.terminate()
        self.close_all_pop_ups()
        # self.thread.wait()

    def run(self):
        if hasattr(ctypes, "windll"):
            # Rename the process so we can get a better icon.
            myappid = f"bw.{APP_NAME.lower()}.1"  # arbitrary string
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        self.main_dialog.show()
        self.app.setWindowIcon(get_icon("tray_icon.png"))
        # Enter Qt application main loop
        self.app.exec()
        sys.exit()

    def thread_download_calendar_finished(self):
        """
        Called when the update thread is finished - all google calendars and events have been donwloaded.
        """
        self.main_dialog.update_now_button.setEnabled(True)
        cur_event_ids = {event.id for event in self.gcal.events}
        for time_event in self.gcal.events:
            if time_event.id not in self.event_alerters:
                self.event_alerters[time_event.id] = EventAlerter(time_event)
            else:
                self.event_alerters[time_event.id].time_event = time_event

        for id in set(self.event_alerters) - cur_event_ids:
            self.event_alerters[id]._alerter.close_pop_ups()
            del self.event_alerters[id]

    def thread_download_calendar_started(self):

        self.main_dialog.time_to_update_label.setText("Updating events...")
        self.main_dialog.update_now_button.setEnabled(False)

    @Slot()
    def tray_clicked(self, reason: QSystemTrayIcon.ActivationReason):
        print("CLICK", reason)
        # reason == QSystemTrayIcon.ActivationReason.Trigger

        self.main_dialog.close()
        self.main_dialog.setVisible(True)
        self.main_dialog.show()
        self.main_dialog.setFocus()
        self.main_dialog.setWindowState(
            self.main_dialog.windowState() & ~Qt.WindowMinimized | Qt.WindowActive
        )
        self.main_dialog.activateWindow()

    def update(self):
        """Main update thread that should be continuously running."""
        # print(QCursor.pos())
        if self.update_calendar_thread.isFinished():
            time_to_update = self.UPDATE_FREQUENCY - (
                time.time() - self.gcal.last_update_time
            )
            if time_to_update <= 0:
                self.update_calendar_thread.start()
            else:
                self.main_dialog.time_to_update_label.setText(
                    f"Updating events in {time_to_update:.0f} seconds"
                )

        for event_alerter in self.event_alerters.values():
            event_alerter.update()

        events = [event_alerter for event_alerter in self.event_alerters.values()]
        self.main_dialog.update_table_with_events(events)
        # self.main_dialog.setSizePolicy(QSizePolicy.Expanding)


def run():  # Entry point for setup.py
    app = App()
    app.run()


if __name__ == "__main__":
    run()
