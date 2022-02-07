# pylint: disable=no-name-in-module
import ctypes
import sys
import webbrowser
from datetime import datetime, timedelta

from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from neverlate.constants import APP_NAME, OUTPUT_DISMISS, OUTPUT_SNOOZE
from neverlate.utils import get_icon, now_datetime, pretty_datetime

LOCAL_TIMEZONE = datetime.now().astimezone().tzinfo

RESTART_TIMER = 15 * 1000  # 15 seconds  (in milliseconds)

SNOOZE_UNTIL_MINUTES = [0, 0.1, 1, 3, 5, 10, 15, 30]  # Minute for the snooze until...
FONT_SIZE_MULTIPLIER = 1  # Multiply font size


class AlertDialog(QDialog):
    """Pop up alert dialog."""

    def __init__(self, title: str, start_time: str, video_uri: str) -> None:
        super().__init__()
        self.start_time = datetime.fromisoformat(start_time)
        self.video_uri = video_uri
        self.setWindowTitle(
            f"Don't Be Late: {title} @ {pretty_datetime(self.start_time)}"
        )
        self.setWindowIcon(get_icon("tray_icon.png"))

        self.start_time_label = QLabel("Starts at: " + pretty_datetime(self.start_time))
        self.start_time_label.setAlignment(Qt.AlignCenter)
        self.time_to_event_label = QLabel(" ")
        self.standard_font_size = self.time_to_event_label.font().pointSize()
        self.time_to_event_label.setAlignment(Qt.AlignCenter)

        self.button_accept = QPushButton("Dismiss")
        self.button_accept.clicked.connect(self.dismiss)
        self.button_join = QPushButton("Joing Meeting")
        if "meet.google" in self.video_uri:
            self.button_join.setText("Join Meeting (Google Meet)")
        self.button_join.clicked.connect(self.dismiss_and_join)
        if not self.video_uri:
            self.button_join.setVisible(False)

        self.snooze_until_combo_box = QComboBox()
        self.snooze_until_combo_box.addItems(["Snooze Until..."])
        self.snooze_until_combo_box.currentIndexChanged.connect(
            self.snooze_until_combo_box_changed
        )
        self.snooze_for_combo_box = QComboBox()
        self.snooze_for_combo_box.addItems(
            ["Snooze for...", "1 min", "3 min", "5 min", "10 min", "15 min", "30 min"]
        )
        self.snooze_for_combo_box.currentTextChanged.connect(
            self.snooze_for_combo_box_changed
        )

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_ui)
        self.update_timer.start(0.9 * 1000)  # 1 sec intervall

        # Auto close the dialog and re-open after X seconds. This makes sure the dialog wasn't opened on a different
        # workspace than the user is currently on.
        # TODO: do NOT
        self.kill_timer = QTimer()
        self.kill_timer.timeout.connect(self.kill_timer_complete)
        self.kill_timer.setSingleShot(True)
        self.kill_timer.start(RESTART_TIMER)

        self.enable_widgets_timer = QTimer()
        self.enable_widgets_timer.timeout.connect(self.enable_widgets)
        self.enable_widgets_timer.start(0.75 * 1000)
        self.enable_widgets(value=False)

        # self.setWindowFlags(Qt.FramelessWindowHint)
        self.layout_ui(title)
        self.update_ui()

    def enable_widgets(self, value: bool = True):
        """Enable buttons.  Auto fired after the app is opened."""
        self.button_join.setEnabled(value)
        self.button_accept.setEnabled(value)

    def layout_ui(self, title: str):
        """Define the main UI layout."""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        main_layout.addStretch()
        main_label = QLabel(title)
        main_label.setAlignment(Qt.AlignCenter)
        font = main_label.font()
        font.setPointSize(self.standard_font_size * 3 * FONT_SIZE_MULTIPLIER)
        font.setBold(True)
        main_label.setFont(font)
        main_layout.addWidget(main_label)
        main_layout.addWidget(self.start_time_label)
        main_layout.addWidget(self.time_to_event_label)

        # Primary buttons
        buttons_layout = QHBoxLayout()
        button_t3 = QPushButton("Snooze for 3 minutes")
        button_t3.clicked.connect(lambda: self.snooze(3))
        button_t1 = QPushButton("Snooze for 1 minute")
        button_t1.clicked.connect(lambda: self.snooze(1))
        buttons_layout.addStretch()
        # buttons_layout.addWidget(button_t3)
        # buttons_layout.addWidget(button_t1)
        buttons_layout.addWidget(self.snooze_until_combo_box)
        buttons_layout.addWidget(self.snooze_for_combo_box)
        buttons_layout.addSpacing(50)
        # buttons_layout.addStretch()
        buttons_layout.addWidget(self.button_join)
        buttons_layout.addWidget(self.button_accept)
        buttons_layout.addStretch()

        main_layout.addSpacing(15)
        main_layout.addLayout(buttons_layout)
        main_layout.addStretch()
        self.setWindowFlags(Qt.WindowStaysOnTopHint)

    def close(self) -> bool:
        # return super().close()
        self.snooze(0)

    def dismiss_and_join(self):
        """Dismiss teh alert, and open the video URI link in a web browser."""
        webbrowser.open(self.video_uri, autoraise=True)
        self.dismiss()

    def dismiss(self):
        """Dismiss the alert permanently."""
        print(OUTPUT_DISMISS)
        sys.exit(0)

    def kill_timer_complete(self):
        """Called when the restart timer ends. If the UI doesn't have focus, restart."""
        # TODO: check if the mouse is over the dialog
        # print(OUTPUT_RESTART)
        self.snooze(0.001)
        # sys.exit(0)

    def update_snooze_for_combo_box_icons(self):
        """Add a warning icon to any combo box item that would make the user late to the meeting."""
        now = now_datetime()
        for idx in range(1, self.snooze_for_combo_box.count()):
            minutes = int(self.snooze_for_combo_box.itemText(idx).split()[0])
            if now + timedelta(minutes=minutes) > self.start_time:
                self.snooze_for_combo_box.setItemIcon(idx, get_icon("warning.png"))

    def update_snooze_until_options(self):
        """Update the valid options for the snooze until"""
        target_items = ["Snooze Until..."]
        current_count = self.snooze_until_combo_box.count()
        for minutes_before in SNOOZE_UNTIL_MINUTES[1:]:
            next_alert_time = self.start_time - timedelta(minutes=int(minutes_before))
            if next_alert_time < now_datetime():
                break
            label = pretty_datetime(next_alert_time)
            if int(minutes_before):
                label += f" ({int(minutes_before)} min before event)"
            target_items.append(label)
        if len(target_items) > current_count:
            self.snooze_until_combo_box.addItems(target_items[1:])
        else:
            while len(target_items) < self.snooze_until_combo_box.count():
                self.snooze_until_combo_box.removeItem(
                    self.snooze_until_combo_box.count() - 1
                )

    def update_ui(self):
        """Update the UI."""
        # If the user is observing the dialog, restart the kill timer
        if self.underMouse():
            self.kill_timer.start(RESTART_TIMER)
        self.update_snooze_for_combo_box_icons()
        self.update_snooze_until_options()
        # self.setWindowTitle(f"Time to event: {self.kill_timer.remainingTime()}")

        now = datetime.now(LOCAL_TIMEZONE)
        seconds_till = (self.start_time - now).total_seconds()
        min_, sec = divmod(int(abs(seconds_till)), 60)
        sec = str(sec).rjust(2, "0")
        hrs, min_ = divmod(min_, 60)
        hrs = f"{hrs}:" if hrs else ""
        min_ = str(min_).rjust(2, "0") if hrs else str(min_)
        if seconds_till <= 0:
            # Late
            self.setWindowIcon(get_icon("warning.png"))
            self.time_to_event_label.setText(
                f"YOU'RE LATE! (How could this happen!?)\nTHE EVENT STARTED {hrs}{min_}:{sec} AGO!!"
            )
            font = self.time_to_event_label.font()
            font.setBold(True)
            font.setPointSize(self.standard_font_size * 2 * FONT_SIZE_MULTIPLIER)
            self.time_to_event_label.setFont(font)
            self.setStyleSheet("background-color: rgb(255, 55, 55);")
            if not self.isMaximized():
                self.showMaximized()
            self.snooze_until_combo_box.setVisible(False)
        else:
            if seconds_till < 60 * 2:
                # Warning!
                self.setStyleSheet("background-color: rgb(255, 245, 55);")

                font = self.time_to_event_label.font()
                font.setBold(True)
                font.setPointSize(15)
                self.time_to_event_label.setFont(font)
            # Plenty of time...
            self.time_to_event_label.setText(f"Time to event: {hrs}{min_}:{sec}")

    def snooze(self, minutes: float):
        """Close the dialog and snooze for X minutes."""
        print(f"{OUTPUT_SNOOZE} {int(minutes * 60)}")
        sys.exit(0)

    @Slot(str)
    def snooze_for_combo_box_changed(self, new_text: str):
        """Callback when the snooze for comobo box is changed."""
        minutes = int(new_text.split()[0])
        self.snooze(minutes)

    @Slot(int)
    def snooze_until_combo_box_changed(self, new_idx: int):
        """Callback when the snooze until combo box is changed."""
        minutes_before = SNOOZE_UNTIL_MINUTES[new_idx]
        next_alert_time = self.start_time - timedelta(minutes=minutes_before)
        time_to_snooze = now_datetime() - next_alert_time
        self.snooze(-time_to_snooze.total_seconds() / 60)


if __name__ == "__main__":
    # _, title, start_time_iso, video_uri = sys.argv
    # start_time = datetime.fromisoformat(start_time_iso)

    app = QApplication()
    if hasattr(ctypes, "windll"):
        # Rename the process so we can get a better icon for Windows
        myappid = f"bw.{APP_NAME.lower()}.dialog" + str(sys.argv[1:])
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    app.setWindowIcon(get_icon("tray_icon.png"))  # Mac OSX
    d = AlertDialog(*sys.argv[1:])  # pylint: disable=no-value-for-parameter
    d.show()
    app.exec()
