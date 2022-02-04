from __future__ import annotations

import os
import subprocess
from datetime import timedelta

from PySide6.QtCore import QThread, Signal, Slot

from neverlate.constants import OUTPUT_DISMISS, OUTPUT_SNOOZE
from neverlate.google_cal_downloader import TimeEvent
from neverlate.utils import now_datetime

# TODO: add a column for attending status, join button, reset time alert button
# TODO: support calendars
# TODO: support preferences

MINUTES_BEFORE_ALERT = 10  # TODO: make this a preference


class EventAlerter:
    time_event: TimeEvent
    has_alerted: bool  # Trure if an alert has been displayed ever
    dismissed_alerts: bool  # True if the user has dismissed the alert dialog
    _alerter: PopUpAlerterThread  # Thread monitoring subprocess for the pop-up dialogs

    def __init__(self, time_event: TimeEvent) -> None:
        self.time_event = time_event
        self.has_alerted = False
        self.dismissed_alerts = False
        self._alerter = PopUpAlerterThread(self.time_event)
        self._alerter.dismissed_signal.connect(self._dismiss_alerts)
        self._alerter.snooze_signal.connect(self.snooze)

    @Slot()
    def _dismiss_alerts(self):
        """
        No longer display alerts for this event.
        """
        self.dismissed_alerts = True

    def reset_alert(self):
        """
        Reset any alerts.
        """
        print("RESET ALERTS!")
        self._alerter.close_pop_ups()
        self.dismissed_alerts = False
        self.has_alerted = False

    @Slot(int)
    def snooze(self, seconds: int = 0) -> None:
        """
        Snooze the alert until now + [seconds].

        Args:
            seconds (int): How many seconds to snooze for.
        """
        self.time_event.start_time = now_datetime() + timedelta(seconds=seconds)

    def time_till_alert(self) -> int:
        """Seconds until a notification should appear.

        Returns:
            int: Seconds till event. Less than zero = do not alert.
        """
        padding = 0 if self.has_alerted else MINUTES_BEFORE_ALERT * 60
        if (
            self.dismissed_alerts
            or self.time_event.has_declined()
            or self.time_event.has_ended()
            or self._alerter.isRunning()  # Already alerted
        ):
            return -1
        secs_till_alert = (self.time_event.start_time - now_datetime()).total_seconds()
        return max(0, int(secs_till_alert) - padding)

    def update(self):
        secs_till = self.time_till_alert()
        if secs_till != 0:
            return
        # Display an alert
        self.has_alerted = True
        self._alerter.start()

    def will_alert(self) -> bool:
        # fmt: off
        if (
            self.dismissed_alerts
            or self.time_event.has_declined()  
            or self.time_event.has_ended() 
            or self._alerter.isRunning()  # Already alerted
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
            output = output.splitlines()[-1] if output else ""
            if output.startswith(OUTPUT_SNOOZE):
                snooze_time = int(output.split()[-1])
                self.snooze_signal.emit(snooze_time)
            elif output.startswith(OUTPUT_DISMISS):
                self.dismissed_signal.emit()
