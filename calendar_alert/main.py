"""Main app entry point."""
from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import time
from datetime import timedelta

from PySide6.QtCore import QRect, Qt, QThread, QTimer, Signal, Slot  # QThreadPool
from PySide6.QtGui import QAction, QCursor, QDesktopServices, QFont, QWindow
from PySide6.QtWidgets import (  # pylint: disable=no-name-in-module
    QAbstractScrollArea,
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSystemTrayIcon,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from calendar_alert.constants import OUTPUT_DISMISS, OUTPUT_SNOOZE
from calendar_alert.directories import get_icon
from calendar_alert.google_cal_downloader import GoogleCalDownloader, TimeEvent
from calendar_alert.preferences import PreferencesDialog
from calendar_alert.utils import now_datetime

TABLE_TITLE = 0
TABLE_EVENT_TIMES = 2
TABLE_END_TIME = 3
TABLE_TIME_TILL_ALERT = 1

# TODO: add a column for attending status
# TODO: changing a time for an event doesn't change the id, causing alert time to NOT be updated!! FIX

MINUTES_BEFORE_ALERT = 10


class EventAlerter:
    def __init__(self, time_event: TimeEvent) -> None:
        self.time_event = time_event
        self.alert_time = time_event.start_time
        self._alert_count = 0
        self.dismissed_alerts = False
        self.alerter = PopUpAlerterThread(self.time_event)
        self.alerter.dismissed_signal.connect(self._dismiss_alerts)
        self.alerter.snooze_signal.connect(self.snooze)

    @Slot()
    def _dismiss_alerts(self):
        """
        No longer display alerts for this event.
        """
        self.dismissed_alerts = True

    def get_seconds_till_alert(self) -> float:
        # TODO: DEPRECATE
        return (self.alert_time - now_datetime()).total_seconds()

    @Slot(int)
    def snooze(self, seconds: int = 0) -> None:
        """
        Snooze the alert until now + [seconds].

        Args:
            seconds (int): How many seconds to snooze for.
        """
        self.alert_time = now_datetime() + timedelta(seconds=seconds)

    def time_till_alert(self) -> int:
        """Seconds until a notification should appear.

        Returns:
            int: Seconds till event. Less than zero = do not alert.
        """
        padding = 0 if self._alert_count else MINUTES_BEFORE_ALERT * 60
        if (
            self.dismissed_alerts
            or self.time_event.has_declined()
            or self.time_event.has_ended()
            or self.alerter.isRunning()  # Already alerted
        ):
            return -1
        secs_till_alert = (self.alert_time - now_datetime()).total_seconds()
        return max(0, int(secs_till_alert) - padding)

    def update(self):
        secs_till = self.time_till_alert()
        if secs_till != 0:
            return
        # Display an alert
        self._alert_count += 1
        self.alerter.start()

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


class PopUpAlerterThread(QThread):

    APP_PATH = os.path.join(os.path.dirname(__file__), "pop_up_alert.py")
    process: subprocess.Popen
    dismissed_signal = Signal()
    snooze_signal = Signal(int)

    def __init__(self, time_event: TimeEvent) -> None:
        super().__init__()

        self.time_event = time_event

    def close_pop_ups(self):
        if self.isRunning():
            self.process.terminate()
            self.terminate()

    def run(self):

        # stdout, stderr = self.process.communicate()
        cmd = ["python", self.APP_PATH]
        cmd += [
            self.time_event.summary,
            self.time_event.start_time.isoformat(),
            self.time_event.get_video_url(),
        ]
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            # shell=True,
        )
        result = self.process.wait()
        output = self.process.stdout.read().decode()  # type: str
        err = self.process.stderr.read().decode()
        if result != 0:
            # Something bad happened. Just alert aga
            print("ERROR:", err)
            return
        else:
            print("Closed event, output:", output)
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
        # TODO: error checking
        from google.auth.exceptions import RefreshError

        try:
            self.calendar.update_calendars()
            self.calendar.update_events()
        except RefreshError:
            print("BAD THINGS HAVE HAPPENED AND NEED TO BE FIXED")
            raise


class MainDialog(QDialog):
    """Main dialog to show general info."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("NeverBeLate")
        # self.setWindowFlags(
        #     Qt.Tool
        # )  # TODO: test / research more https://doc.qt.io/qt-5/qt.html#WindowType-enum
        self.setWindowIcon(get_icon("tray_icon.png"))
        self.update_now_button = QPushButton("Update Now")
        self.quit_button = QPushButton("Exit App")
        self.debug_button = QPushButton("Debug Tester")
        self.time_to_update_label = QLabel()

        self.event_table = QTableWidget(0, 3)
        self.event_table.setHorizontalHeaderItem(TABLE_TITLE, QTableWidgetItem("Event"))
        self.event_table.setHorizontalHeaderItem(
            TABLE_EVENT_TIMES, QTableWidgetItem("Time")
        )
        self.event_table.setHorizontalHeaderItem(
            TABLE_TIME_TILL_ALERT, QTableWidgetItem("Tim Till Alert")
        )
        # self.event_table.horizontalHeader().hide()
        self.event_table.verticalHeader().hide()
        self.event_table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.event_table)
        main_layout.addWidget(self.debug_button)
        # main_layout.addStretch()

        layout = QHBoxLayout()
        layout.addStretch()
        layout.addWidget(self.time_to_update_label)
        layout.addWidget(self.update_now_button)

        main_layout.addLayout(layout)
        main_layout.addWidget(self.quit_button)
        self.setLayout(main_layout)

    def update_table_with_events(self, alerters: list[EventAlerter]):

        self.event_table.setRowCount(len(alerters))
        alerters.sort(key=lambda a: a.time_event.start_time)
        now = now_datetime()
        for idx, alerter in enumerate(alerters):
            # font = item.font()  # type: QFont
            # font.setStrikeOut(True)
            # item.setFont(font)

            self.event_table.setItem(
                idx, TABLE_TITLE, QTableWidgetItem(alerter.time_event.summary)
            )

            # Start time
            start_time = alerter.time_event.start_time.strftime("%I:%M")
            if start_time[0] == "0":
                start_time = start_time[1:]

            # End time
            end_time = alerter.time_event.end_time.strftime("%I:%M %p")
            if end_time[0] == "0":
                end_time = end_time[1:]

            self.event_table.setItem(
                idx,
                TABLE_EVENT_TIMES,
                QTableWidgetItem(f"{start_time} - {end_time}"),
            )

            # Time till alert
            time_till_alert = alerter.time_till_alert()
            if time_till_alert <= 0:
                time_till_alert = "---"
            else:
                min_, secs = divmod(time_till_alert, 60)
                hours, min_ = divmod(min_, 60)
                if hours:
                    secs = str(secs).zfill(2)
                    min_ = str(min_).zfill(2)
                    time_till_alert = f"{hours}:{min_}:{secs}"
                else:
                    secs = str(secs).zfill(2)
                    time_till_alert = f"{min_}:{secs}"

                time_till_alert = str(time_till_alert)

            self.event_table.setItem(
                idx,
                TABLE_TIME_TILL_ALERT,
                QTableWidgetItem(time_till_alert),
            )

            if alerter.time_event.has_declined():
                for column in range(self.event_table.columnCount()):
                    item = self.event_table.item(idx, column)
                    font = QFont()
                    font.setItalic(True)
                    font.setStrikeOut(True)
                    item.setFont(font)

        self.event_table.resizeColumnsToContents()


class App:
    """Main calendar_alert Qt application."""

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
        self.main_dialog.debug_button.clicked.connect(self._undismiss_events)

        # Size of initial window
        rect = QRect(0, 0, 600, 300)
        screen_geo = self.app.primaryScreen().geometry()
        rect.moveCenter(screen_geo.center())
        self.main_dialog.setGeometry(rect)

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

        self.event_alerters = {}  # type: dict[str, EventAlerter]

    def _undismiss_events(self):

        for event in self.event_alerters.values():
            if event.alerter.isRunning():
                event.alerter.process.terminate()
                event.alerter.terminate()
            event.dismissed_alerts = False
            event._alert_count = 0

    def on_update_now(self):
        print("ON UPDATE NOW")
        # self.gcal.last_update_time = 0.0
        self.update_calendar_thread.start()
        self.update()

    def update_thread_finished(self):
        """
        Called when the update thread is finished - all google calendars and events have been donwloaded.
        """
        # TODO: support for changing / disabling calendars
        self.main_dialog.update_now_button.setEnabled(True)
        cur_event_ids = {event.id for event in self.gcal.events}
        for time_event in self.gcal.events:
            if time_event.id not in self.event_alerters:
                self.event_alerters[time_event.id] = EventAlerter(time_event)
            else:
                self.event_alerters[time_event.id].time_event = time_event

        for id in set(self.event_alerters) - cur_event_ids:
            self.event_alerters[id].alerter.close_pop_ups()
            del self.event_alerters[id]

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
        """Quitting the app. Make sure we terminate all threads first."""
        self.update_calendar_thread.finished.disconnect()
        self.update_calendar_thread.terminate()
        self.close_all_pop_ups()
        # self.thread.wait()

    def run(self):
        if hasattr(ctypes, "windll"):
            # Rename the process so we can get a better icon.
            myappid = "bw.calendar_alert.1"  # arbitrary string
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        self.main_dialog.show()
        self.app.setWindowIcon(get_icon("tray_icon.png"))
        # Enter Qt application main loop
        self.app.exec()
        sys.exit()

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

    def close_all_pop_ups(self):

        for event in self.event_alerters.values():
            event.alerter.close_pop_ups()

    def update(self):
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


if __name__ == "__main__":
    app = App()
    app.run()
