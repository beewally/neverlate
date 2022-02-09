"""Main app entry point."""
# pylint: disable=no-name-in-module
from __future__ import annotations

import ctypes
import sys
import time
import traceback

from google.auth.exceptions import RefreshError
from PySide6.QtCore import QRect, Qt, QThread, QTimer, Slot
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from neverlate.constants import APP_NAME
from neverlate.event_alerter import EventAlerter
from neverlate.google_cal_downloader import GoogleCalDownloader
from neverlate.main_dialog import MainDialog
from neverlate.preferences import PreferencesDialog
from neverlate.utils import get_icon, now_datetime

# TODO: add a column for attending status, join button, reset time alert button
# TODO: support calendars
# TODO: support preferences
# TODO: make it prettier for mac osx dark theme (just handle/bypass OS themes altogether?)


class UpdateCalendar(QThread):
    """Thread to download google calendars + events."""

    def __init__(self, calendar: GoogleCalDownloader) -> None:
        super().__init__()
        self.calendar = calendar

    def run(self):
        """Main entry point.

        Raises:
            RefreshError: When unable to download the calendar events for some reason.
        """
        # TODO: handle internet outtage/unresponsive google (in addition to token expirations)
        try:
            self.calendar.update_calendars()
            self.calendar.update_events()
        except RefreshError:
            print("BAD THINGS HAVE HAPPENED AND NEED TO BE FIXED")
            raise
        except ConnectionResetError:
            print("!!!!!!!!!!! CONNETION RESET ERROR!!!!!!!!!!!!!!", now_datetime())
        except:
            print("=" * 80)
            print(traceback.format_exc())
            print("=" * 80)
            print("Unknown bad things have happened!!", now_datetime())


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
        main_dialog_action = menu.addAction("Show Overview")
        main_dialog_action.triggered.connect(self.show_main_dialog)
        setting_action = menu.addAction("Show Preferences")
        setting_action.triggered.connect(self.preferences_dialog.show)
        exit_action = menu.addAction("Quit")
        exit_action.triggered.connect(self.app.exit)
        self.tray = QSystemTrayIcon()
        self.tray.activated.connect(self.tray_clicked)
        self.tray.setIcon(get_icon("tray_icon.png"))
        self.tray.setContextMenu(menu)
        self.tray.show()
        self.tray.setToolTip("Never late!")
        # self.tray.showMessage(
        #     "My Great Title",
        #     "You're late for an event!",
        #     get_icon("tray_icon.png"),
        # )

    def on_update_now(self):
        """User manually requested the calanders be re-downloaded."""
        self.update_calendar_thread.start()
        self.update()

    def quitting(self) -> None:
        """Quitting the app. Make sure we terminate all threads first."""
        self.update_calendar_thread.finished.disconnect()
        self.update_calendar_thread.terminate()
        for event in self.event_alerters.values():
            event.close_pop_up()

    def run(self):
        """Start the application."""
        if hasattr(ctypes, "windll"):
            # Rename the process so we can get a better icon.
            myappid = f"bw.{APP_NAME.lower()}.1"  # arbitrary string
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        # self.main_dialog.show()
        self.app.setWindowIcon(get_icon("tray_icon.png"))
        # Enter Qt application main loop
        self.app.exec()
        sys.exit()

    def show_main_dialog(self):
        """Show's the main dialog - forcing it to be on top."""
        # TODO: make this work for the preferences dialog (?)
        if sys.platform == "darwin":
            if self.main_dialog.isVisible():
                self.main_dialog.close()

            self.main_dialog.setWindowFlags(Qt.WindowStaysOnTopHint)
            self.main_dialog.show()
            return

        # Else: Windows/Linux
        if self.main_dialog.isVisible():
            # Close the dialog and re-open. This way we don't force the user to switch desktops/workspaces.
            self.main_dialog.close()
        self.main_dialog.setWindowFlags(
            # Qt.Tool  # Tool makes it visible on all workspaces/desktops for Windows
            Qt.Dialog
        )  # TODO: test / research more https://doc.qt.io/qt-5/qt.html#WindowType-enum
        self.main_dialog.show()
        self.main_dialog.activateWindow()

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

        for id_ in set(self.event_alerters) - cur_event_ids:
            self.event_alerters[id_].close_pop_up()
            del self.event_alerters[id_]

    def thread_download_calendar_started(self):
        """Called when the thread to download calendars + events is triggered. Updates the UI accordingly."""
        self.main_dialog.time_to_update_label.setText("Updating events...")
        self.main_dialog.update_now_button.setEnabled(False)

    @Slot()
    def tray_clicked(self, reason: QSystemTrayIcon.ActivationReason):
        """Callback when the user clicks on the tray icon in the task bar. Should show various options/show the
        main GUI.
        """
        if sys.platform == "darwin":
            if reason == QSystemTrayIcon.ActivationReason.Trigger:
                return  # Mac OSX always shows the menu on left click (Trigger)
            else:
                print("UNHANDLED TRAY CLICK:", reason)
        else:
            # Windows/Linux
            if reason in (
                QSystemTrayIcon.ActivationReason.Trigger,
                QSystemTrayIcon.ActivationReason.DoubleClick,
            ):
                # Force show the main dialog
                if self.main_dialog.isVisible():
                    self.main_dialog.close()
                else:
                    self.show_main_dialog()

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


def run():
    """Console tool entry point/ when run as __main__"""
    app = App()
    app.run()


if __name__ == "__main__":
    run()
