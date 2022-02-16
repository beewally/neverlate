from __future__ import annotations

import typing
from datetime import timedelta

from PySide6.QtCore import QRect, Qt, QThread, QTimer, Signal, Slot  # QThreadPool
from PySide6.QtGui import QAction, QColor, QCursor, QDesktopServices, QFont, QWindow
from PySide6.QtWidgets import (  # pylint: disable=no-name-in-module
    QAbstractScrollArea,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from neverlate.utils import get_icon, now_datetime, pretty_datetime


class LoginDialog(QDialog):
    """Main dialog to show general info."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("NeverLate: Login")
        self.setWindowIcon(get_icon("tray_icon.png"))
        # self.setWindowFlag(Qt.Dialog)
        self.setWindowModality(Qt.ApplicationModal)

        main_layout = QVBoxLayout()
        main_layout.addWidget(
            QLabel(
                "Welcome to NeverLate!\n"
                "To get started, you need to log in to Google.\n"
                "Pressing 'Login' will open up your browser asking you to log in."
            )
        )
        self.login_button = QPushButton("Login")
        self.quit_button = QPushButton("Quit")
        self.quit_button.pressed.connect(self.reject)
        self.login_button.pressed.connect(self.accept)

        layout = QHBoxLayout()
        layout.addStretch()
        layout.addWidget(self.login_button)
        layout.addWidget(self.quit_button)

        main_layout.addLayout(layout)

        self.setLayout(main_layout)
