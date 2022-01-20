"""Main app entry point."""
import ctypes
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pprint import pprint as pp
from typing import Any, Dict, Optional, Union

from PySide6.QtCore import Qt, QThread, QThreadPool, QTimer, Signal, Slot
from PySide6.QtGui import QAction, QCursor, QDesktopServices, QWindow
from PySide6.QtWidgets import (  # pylint: disable=no-name-in-module
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSystemTrayIcon,
    QVBoxLayout,
)

from calendar_alert.constants import OUTPUT_DISMISS, OUTPUT_SNOOZE
from calendar_alert.directories import get_icon
from calendar_alert.google_cal_downloader import GoogleCalDownloader, TimeEvent
from calendar_alert.preferences import PreferencesDialog

LOCAL_TIMEZONE = datetime.now().astimezone().tzinfo


class EventAlerter:
    def __init__(self, time_event: TimeEvent) -> None:
        self.time_event = time_event
        self.alert_time = time_event.start_time
        self._alert_count = 0
        self.dismissed_alerts = False
        self.alerter = PopUpAlerter(self.time_event)
        self.alerter.dismissed_signal.connect(self._dismiss_alerts)
        self.alerter.snooze_signal.connect(self.snooze)

    def get_seconds_till_alert(self) -> float:
        now = datetime.now(LOCAL_TIMEZONE)
        return (self.alert_time - now).total_seconds()

    @Slot(int)
    def snooze(self, seconds: int = 0) -> None:
        """
        Snooze the alert until now + [seconds].

        Args:
            seconds (int): How many seconds to snooze for.
        """
        self.alert_time = datetime.now(LOCAL_TIMEZONE) + timedelta(seconds=seconds)

    def update(self, seconds_before_first_alert: int):
        padding = 0 if self._alert_count else seconds_before_first_alert
        if (
            self.dismissed_alerts
            or self.time_event.has_declined()
            or self.time_event.has_ended()
            or self.alerter.isRunning()  # Already alerted
            or self.get_seconds_till_alert() - padding > 0
        ):
            return
        # Display an alert
        self._alert_count += 1
        self.alerter.start()

    @Slot()
    def _dismiss_alerts(self):
        """
        No longer display alerts for this event.
        """
        self.dismissed_alerts = True

    def will_alert(self) -> bool:
        # fmt: off
        if (
            self.dismissed_alerts
            or self.time_event.has_declined()  
            or self.time_event.has_ended() 
            or self.alerter.isRunning()  # Already alerted
        ):
            return False
        # fmt: on
        return True


class PopUpAlerter(QThread):

    APP_PATH = os.path.join(os.path.dirname(__file__), "pop_up_alert.py")
    process: subprocess.Popen
    dismissed_signal = Signal()
    snooze_signal = Signal(int)

    def __init__(self, time_event: TimeEvent) -> None:
        super().__init__()

        self.time_event = time_event

    def run(self):

        # stdout, stderr = self.process.communicate()
        cmd = ["python", self.APP_PATH]
        cmd += [
            self.time_event.summary,
        ]
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            # shell=True,
        )
        result = self.process.wait()
        output = self.process.stdout.read().decode()  # type: str
        if result != 0:
            # Something bad happened. Just alert again
            self.dismissed = False
            self.snooze_time = 0
        else:
            if output.startswith(OUTPUT_SNOOZE):
                snooze_time = int(output.split()[-1])
                self.snooze_signal.emit(snooze_time)
            elif output.startswith(OUTPUT_DISMISS):
                self.dismissed_signal.emit()


class UpdateCalendar(QThread):
    def __init__(self, calendar: GoogleCalDownloader) -> None:
        super().__init__()
        self.calendar = calendar

    def run(self):
        print("Updating calendars in thread...")
        # time.sleep(12)
        self.calendar.update_calendars()
        self.calendar.update_events()


class MainDialog(QDialog):
    """Main dialog to show general info."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Event Notifier")
        self.setWindowIcon(get_icon("tray_icon.png"))
        self.update_now_button = QPushButton("Update Now")
        self.quit_button = QPushButton("Press to quit")
        self.debug_button = QPushButton("Debug Thing - Terminate All Dialogs")
        self.time_to_update_label = QLabel()

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.debug_button)
        main_layout.addStretch()
        layout = QHBoxLayout()
        layout.addWidget(self.time_to_update_label)
        layout.addWidget(self.update_now_button)
        main_layout.addLayout(layout)
        main_layout.addWidget(self.quit_button)
        self.setLayout(main_layout)


class App:
    """Main calendar_alert Qt application."""

    UPDATE_FREQUENCY = 30  # seconds to wait before updating events
    MINUTES_BEFORE_ALERT = 10

    tray: QSystemTrayIcon

    def __init__(self) -> None:
        # Create a Qt application
        self.app = QApplication(sys.argv)
        self.app.aboutToQuit.connect(self.quitting)
        self.app.setQuitOnLastWindowClosed(False)
        # self.app.setWindowIcon(get_icon("tray_icon.png"))  # DOesn't seem to work
        self.main_dialog = MainDialog()
        self.main_dialog.quit_button.clicked.connect(self.app.quit)
        self.main_dialog.update_now_button.clicked.connect(self.on_update_now)
        self.main_dialog.debug_button.clicked.connect(self.terminate_alert_apps)

        self.preferences_dialog = PreferencesDialog()
        self._setup_tray()

        # Log in & get google calendar events
        self.gcal = GoogleCalDownloader()

        self.calendars = self.gcal.update_calendars()

        # Timer - runs in the main thread every 1 second
        self.my_timer = QTimer()
        self.my_timer.timeout.connect(self.update)
        self.my_timer.start(1 * 1000)  # 1 sec intervall

        self.update_calendar_thread = UpdateCalendar(self.gcal)
        self.update_calendar_thread.finished.connect(self.update_thread_finished)
        self.update_calendar_thread.started.connect(self.update_thread_started)
        self.update_calendar_thread.start()

        self.alert_apps: list[PopUpAlerter] = []  # TODO: deprecate
        self.event_alerters = {}  # type: Dict[str, EventAlerter]

    def on_update_now(self):
        print("ON UPDATE NOW")
        # self.gcal.last_update_time = 0.0
        self.update_calendar_thread.start()
        self.update()

    def update_thread_finished(self):
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
            print("DELETED:", id)
            # TODO: process

    def update_thread_started(self):

        self.main_dialog.time_to_update_label.setText("Updating events...")
        self.main_dialog.update_now_button.setEnabled(False)

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

    def quitting(self) -> None:
        print("QUITTING")
        self.update_calendar_thread.finished.disconnect()
        self.update_calendar_thread.terminate()
        self.terminate_alert_apps()
        # self.thread.wait()

    def run(self):
        if hasattr(ctypes, "windll"):
            # Rename the process so we can get a better icon.
            myappid = "bw.calendar_alert.1"  # arbitrary string
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        self.main_dialog.show()
        # Enter Qt application main loop
        self.app.exec()
        sys.exit()

    @Slot()
    def tray_clicked(self, reason: QSystemTrayIcon.ActivationReason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.main_dialog.setVisible(not self.main_dialog.isVisible())
            print("TRAY CLICKED")

    def terminate_alert_apps(self):

        for event in self.event_alerters.values():
            if event.alerter.isRunning():
                event.alerter.process.terminate()
                event.alerter.terminate()

    def update(self):
        # print(QCursor.pos())
        # for i, app in enumerate(self.alert_apps[:]):
        #    if app.process.poll() == None:
        #        continue

        # print(i, app.title, app.process.poll(), app.process.stdout.read())
        # self.alert_apps = []
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

        print("=" * 80)
        for event_alerter in self.event_alerters.values():
            event_alerter.update(
                seconds_before_first_alert=self.MINUTES_BEFORE_ALERT * 60
            )
        # else:
        #    self.main_dialog.time_to_update_label.setText("Updating events2...")
        #    print(
        #        "   Updating cal in:",
        #        self.UPDATE_FREQUENCY - (time.time() - self.gcal.last_update_time),
        #    )


if __name__ == "__main__":
    app = App()
    app.run()
