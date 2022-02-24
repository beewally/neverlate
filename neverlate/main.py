"""Main app entry point."""
# pylint: disable=no-name-in-module
from __future__ import annotations

import ctypes
import logging
import sys
import time
import traceback
import typing

from google.auth.exceptions import RefreshError
from PySide6.QtCore import QRect, Qt, QThread, QTimer, Slot
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from neverlate.constants import APP_NAME
from neverlate.event_alerter import EventAlerter
from neverlate.google_cal_downloader import GoogleCalDownloader
from neverlate.login_dialog import LoginDialog
from neverlate.main_dialog import MainDialog
from neverlate.preferences import PREFERENCES
from neverlate.preferences_dialog import PreferencesDialog
from neverlate.utils import get_icon, seconds_to_min_sec

# TODO: add a column for attending status, join button, reset time alert button
# TODO: support calendars
# TODO: support preferences
# TODO: make it prettier for mac osx dark theme (just handle/bypass OS themes altogether?)

if typing.TYPE_CHECKING:
    from PySide6.QtWidgets import QDialog


logger = logging.getLogger("NeverLate")


class UpdateCalendar(QThread):
    """Thread to download google calendars + events."""

    def __init__(self, calendar: GoogleCalDownloader) -> None:
        super().__init__()
        self.gcal = calendar
        self.needs_login = False

    def run(self):
        """Main entry point.

        Raises:
            RefreshError: When unable to download the calendar events for some reason.
        """
        self.needs_login = False
        try:
            self.gcal.update_calendars()
            calendars_to_update = [
                cal
                for cal in self.gcal.calendars
                if PREFERENCES.calendar_visibility.get(cal.id, cal.selected)
            ]
            self.gcal.update_events(calendars=calendars_to_update)
        except RefreshError:
            logger.error("BAD THINGS HAVE HAPPENED AND NEED TO BE FIXED")
            self.needs_login = True
        except ConnectionResetError:
            logger.debug(
                "ConnectionResetError while trying to download calendars + events. (Will try again)"
            )
        except ConnectionAbortedError:
            logger.debug(
                "ConnectionAbortedError error while trying to download calendars + events. (Will try again)"
            )
        except:
            line = "=" * 80
            logger.error("%s\n%s\n%s", line, traceback.format_exc(), line)


class App:
    """Main Qt application."""

    app: QApplication
    tray: QSystemTrayIcon
    preferences_dialog: PreferencesDialog

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
        self.preferences_dialog.logout_button.pressed.connect(
            lambda: self.login(force=True)
        )
        self._setup_tray()

        # Log in & get google calendar events
        self.gcal = GoogleCalDownloader()
        self.login()

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
        setting_action.triggered.connect(self.show_preferences_dialog)
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

    def _show_dialog(self, dialog: QDialog):
        """Show a dialog - and if it's already visibile, try to bring it to the front. (This logic varies a good bit
        per OS.)

        Args:
            dialog (QDialog): Dialog to show.
        """
        if sys.platform == "darwin":
            if dialog.isVisible():
                dialog.close()

            dialog.setWindowFlags(Qt.WindowStaysOnTopHint)
            dialog.show()
            return

        # Else: Windows/Linux
        if dialog.isVisible():
            # Close the dialog and re-open. This way we don't force the user to switch desktops/workspaces.
            dialog.close()
        dialog.setWindowFlags(
            # Qt.Tool  # Tool makes it visible on all workspaces/desktops for Windows
            Qt.Dialog
        )  # TODO: test / research more https://doc.qt.io/qt-5/qt.html#WindowType-enum
        dialog.show()
        dialog.activateWindow()

    def login(self, force: bool = False):
        """Log into Google!

        Args:
            force (bool, optional): Force the user to re-log in.. Defaults to False.
        """
        if force:
            self.gcal.logout()
        elif self.gcal.login(require_existing_credentials=True):
            try:
                self.gcal.update_calendars()
                return
            except RefreshError:
                # Likely the user needs to log in again (credential issue)
                pass
        login_dialog = LoginDialog()
        login_dialog.login_button.pressed.connect(self.main_dialog.hide)
        login_dialog.login_button.pressed.connect(self.gcal.login)
        result = login_dialog.exec()
        if result == 0:  # User quit
            self.app.quit()  # TODO: test when in threads
            return sys.exit()

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
        self.main_dialog.show()  # TODO: enable/disable? just first time you launch?

        # Enter Qt application main loop
        self.app.exec()

    def show_main_dialog(self):
        """Show's the main dialog - forcing it to be on top."""
        # TODO: make this work for the preferences dialog (?)

        self._show_dialog(self.main_dialog)

        # Make sure the UI is up to date with the latest events
        self.update()

    def show_preferences_dialog(self):
        """Show the preferences dialog. Make sure it has the latest calendars."""
        self.preferences_dialog.update_calendars(self.gcal.calendars)
        self._show_dialog(self.preferences_dialog)

    def thread_download_calendar_finished(self):
        """
        Called when the update thread is finished - all google calendars and events have been donwloaded.
        """
        # Check if there was an error
        if self.update_calendar_thread.needs_login:
            mb = QMessageBox()
            mb.setWindowTitle("NeverLate: Logged Out")
            mb.setIcon(QMessageBox.Critical)
            mb.setText("You have been logged out of Google. Please log back in.")
            mb.setDetailedText(
                "This happened because this app has not been verified by Google yet, which requires "
                "testers to re-login once a week."
            )
            mb.setStandardButtons(QMessageBox.Ok)
            mb.exec()
            self.login(force=True)
            self.update_calendar_thread.start()
            return

        # Update the GUI
        self.main_dialog.update_now_button.setEnabled(True)

        # Check if new calendars need to be saved
        save_prefs = False
        for cal in self.gcal.calendars:
            if cal.id not in PREFERENCES.calendar_visibility:
                PREFERENCES.calendar_visibility[cal.id] = cal.selected
                save_prefs = True

        if save_prefs:
            PREFERENCES.save()

        # Process new/old events (close pop-ups for deleted events)
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
                logger.debug("UNHANDLED TRAY CLICK: %s", reason)
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
        QMenu()
        if (
            not self.update_calendar_thread.needs_login
            and self.update_calendar_thread.isFinished()
        ):
            time_to_update = (PREFERENCES.download_cal_freq * 60) - (
                time.time() - self.gcal.last_update_time
            )
            if time_to_update <= 0:
                self.update_calendar_thread.start()
            else:
                time_label = seconds_to_min_sec(int(time_to_update))
                self.main_dialog.time_to_update_label.setText(
                    f"Updating events in {time_label}"
                )

        display_events = []
        for event_alerter in self.event_alerters.values():
            if not PREFERENCES.calendar_visibility.get(
                event_alerter.time_event.calendar.id, False
            ):
                # Calendar is not enabled, close pop-ups and move on
                # TODO: broken?
                event_alerter.close_pop_up()
            else:
                event_alerter.update()
                display_events.append(event_alerter)
        if self.main_dialog.isVisible():
            self.main_dialog.update_table_with_events(display_events)
        # self.main_dialog.setSizePolicy(QSizePolicy.Expanding)


def run():
    """Console tool entry point/ when run as __main__"""
    logging.basicConfig(
        level=logging.WARNING,
        format="NeverLate: %(asctime)s %(levelname)s : %(message)s",
    )
    if "--verbose" in sys.argv or "-v" in sys.argv:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose mode is enabled!")

    app = App()
    app.run()


if __name__ == "__main__":
    run()
