# make stdin a non-blocking file
import sys
import time
import webbrowser
from datetime import datetime
from enum import auto
from pprint import pprint as pp
from typing import Any

from PySide6.QtCore import Qt, QThread, QThreadPool, QTimer, Signal, Slot
from PySide6.QtGui import QAction, QCursor, QDesktopServices, QWindow
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QVBoxLayout,
)

from calendar_alert.constants import OUTPUT_DISMISS, OUTPUT_SNOOZE

LOCAL_TIMEZONE = datetime.now().astimezone().tzinfo


class AlertDialog(QDialog):
    def __init__(self, title: str, start_time: str, video_uri: str) -> None:
        super().__init__()
        self.start_time = datetime.fromisoformat(start_time)
        self.video_uri = video_uri
        # TODO: icon
        self.setWindowTitle(f"It's Time To Do Something: {title}")

        main_label = QLabel(title)
        main_label.setAlignment(Qt.AlignCenter)
        font = main_label.font()
        font.setPointSize(font.pointSize() * 3)
        main_label.setFont(font)

        self.time_to_event_label = QLabel(" ")
        self.time_to_event_label.setAlignment(Qt.AlignCenter)
        main_layout = QVBoxLayout()
        main_layout.addWidget(main_label)
        main_layout.addWidget(self.time_to_event_label)

        buttons_layout = QHBoxLayout()
        button_t3 = QPushButton("Snooze for 3 minutes")
        button_t3.clicked.connect(lambda: self.snooze(3))

        button_t1 = QPushButton("Snooze for 1 minute")
        button_t1.clicked.connect(lambda: self.snooze(1))

        self.button_join = QPushButton("Open Video URL")
        self.button_join.clicked.connect(self.dismiss_and_join)
        if not self.video_uri:
            self.button_join.setVisible(False)

        button_accept = QPushButton("Dismiss")
        button_accept.clicked.connect(self.dismiss)

        buttons_layout.addWidget(button_t3)
        buttons_layout.addWidget(button_t1)
        buttons_layout.addSpacing(50)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.button_join)
        buttons_layout.addWidget(button_accept)
        main_layout.addStretch()
        main_layout.addLayout(buttons_layout)
        self.setLayout(main_layout)
        self.ui_update()

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.ui_update)
        self.update_timer.start(1 * 1000)  # 1 sec intervall

        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        # self.setWindowFlags(Qt.FramelessWindowHint)

    def close(self) -> bool:
        # return super().close()
        self.snooze(0.5)

    def dismiss_and_join(self):
        webbrowser.open(self.video_uri, autoraise=True)
        self.dismiss()

    def dismiss(self):
        print(OUTPUT_DISMISS)
        sys.exit(0)

    def ui_update(self):

        now = datetime.now(LOCAL_TIMEZONE)
        seconds_till = (self.start_time - now).total_seconds()
        min_, sec = divmod(int(abs(seconds_till)), 60)
        sec = str(sec).rjust(2, "0")
        hrs, min_ = divmod(min_, 60)
        hrs = f"{hrs}:" if hrs else ""
        min_ = str(min_).rjust(2, "0") if hrs else str(min_)
        if seconds_till <= 0:
            self.time_to_event_label.setText(
                f"YOU'RE LATE! (How did this happen!?)\nYOUR MEETING STARTED {hrs}{min_}:{sec} AGO!!"
            )
            font = self.time_to_event_label.font()
            font.setBold(True)
            self.time_to_event_label.setFont(font)
            self.setStyleSheet("background-color: rgb(255, 55, 55);")
        elif seconds_till < 60 * 2:
            self.setStyleSheet("background-color: rgb(255, 245, 55);")
        else:
            self.time_to_event_label.setText(f"Time to event: {hrs}{min_}:{sec}")

    def snooze(self, minutes: float):
        print(f"{OUTPUT_SNOOZE} {int(minutes * 60)}")
        sys.exit(0)


if __name__ == "__main__":
    # _, title, start_time_iso, video_uri = sys.argv
    # start_time = datetime.fromisoformat(start_time_iso)
    app = QApplication()
    d = AlertDialog(*sys.argv[1:])
    d.show()
    app.exec()
