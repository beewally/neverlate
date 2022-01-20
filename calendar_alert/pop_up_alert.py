# make stdin a non-blocking file
import sys
import time
import webbrowser
from enum import auto
from pprint import pprint as pp
from typing import Any

from PySide6.QtCore import Qt, QThread, QThreadPool, QTimer, Signal, Slot
from PySide6.QtGui import QAction, QCursor, QDesktopServices, QWindow
from PySide6.QtWidgets import (  # pylint: disable=no-name-in-module
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from calendar_alert.constants import OUTPUT_DISMISS, OUTPUT_SNOOZE


class AlertDialog(QDialog):
    def __init__(self, title: str) -> None:
        super().__init__()
        label = QLabel(f"Hello world: {title}")
        main_layout = QVBoxLayout()
        main_layout.addWidget(label)

        buttons_layout = QHBoxLayout()
        button_t3 = QPushButton("Snooze for 3 minutes")
        button_t3.clicked.connect(lambda: self.snooze(3))

        button_t1 = QPushButton("Snooze for 1 minute")
        button_t1.clicked.connect(lambda: self.snooze(1))

        self.button_join = QPushButton("Dismiss & Open Meeting")
        self.button_join.clicked.connect(self.dismiss_and_join)

        button_accept = QPushButton("Dismiss")
        button_accept.clicked.connect(self.dismiss)

        buttons_layout.addWidget(button_t3)
        buttons_layout.addWidget(button_t1)
        buttons_layout.addSpacing(10)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.button_join)
        buttons_layout.addWidget(button_accept)
        main_layout.addStretch()
        main_layout.addLayout(buttons_layout)
        self.setLayout(main_layout)

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.ui_update)
        self.update_timer.start(1 * 1000)  # 1 sec intervall

        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        # self.setWindowFlags(Qt.FramelessWindowHint)

    def dismiss_and_join(self):
        webbrowser.open("http://www.google.com", autoraise=True)
        self.dismiss()

    def dismiss(self):
        print(OUTPUT_DISMISS)
        sys.exit(0)

    def ui_update(self):
        pass

    def snooze(self, minutes: float):
        print(f"{OUTPUT_SNOOZE} {minutes * 60}")
        sys.exit(0)


if __name__ == "__main__":
    # print("BEGINING ANOTHER PROCESS")
    _, title = sys.argv
    app = QApplication()
    d = AlertDialog(title)
    d.show()
    app.exec()
