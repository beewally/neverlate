"""Main app entry point."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from neverlate.preferences import PREFERENCES
from neverlate.utils import get_icon

if TYPE_CHECKING:
    from neverlate.google_cal_downloader import Calendar

# pylint: disable=no-name-in-module


# TODO: implement


class PreferencesDialog(QDialog):  # pylint: disable=too-few-public-methods
    """Preferences dialog panes"""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Preferences")
        self.setWindowIcon(get_icon("tray_icon.png"))

        self.alert_padding_sb = QSpinBox()
        self.alert_padding_sb.setValue(PREFERENCES.alert_padding)

        self.download_cal_freq_sb = QSpinBox()
        self.download_cal_freq_sb.setValue(PREFERENCES.download_cal_freq)
        self.download_cal_freq_sb.setMinimum(3)

        # Close buttons
        self.apply_button = QPushButton("Apply")
        self.apply_button.pressed.connect(self.save)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.pressed.connect(self.close)
        # self.button.clicked.connect(close_s)
        self.scroll_widget = QWidget()
        self.calendars = []  # type: list[Calendar]
        self.calendar_toggles = {}  # type: dict[str, QCheckBox]

        self.layout_ui()

    def layout_ui(self):
        """Lays out all the UI elements"""
        main_layout = QVBoxLayout()

        toggle_layout = QFormLayout()
        toggle_layout.addRow(
            "Minutes before an event to show an alert dialog", self.alert_padding_sb
        )
        toggle_layout.addRow(
            "Frequency in minutes to check for new events", self.download_cal_freq_sb
        )
        main_layout.addLayout(toggle_layout)

        # Calendars
        main_layout.addWidget(QLabel("Calendar(s)"))
        scroll_area = QScrollArea()
        scroll_layout = QVBoxLayout()
        scroll_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area.setWidget(self.scroll_widget)
        self.scroll_widget.setLayout(scroll_layout)
        scroll_area.setWidgetResizable(True)
        # scroll_area.setFixedHeight(200)
        # scroll_area.setMaximumHeight(600)
        scroll_area.setMinimumHeight(130)
        main_layout.addWidget(scroll_area)

        # Close/accept buttons
        button_box = QHBoxLayout()
        button_box.addStretch()
        button_box.addWidget(self.apply_button)
        button_box.addWidget(self.cancel_button)
        main_layout.addLayout(button_box)

        self.setLayout(main_layout)
        self.adjustSize()

    def save(self):
        """Save the preferences and close the dialog."""
        PREFERENCES.alert_padding = self.alert_padding_sb.value()
        PREFERENCES.download_cal_freq = self.download_cal_freq_sb.value()
        PREFERENCES.calendar_visibility = {
            id_: toggle.isChecked() for id_, toggle in self.calendar_toggles.items()
        }

        PREFERENCES.save()
        self.close()

    def update_calendars(self, calendars: list[Calendar]):
        """Display toggles for all calendar(s)"""

        num_items = len(self.calendar_toggles)
        self.calendar_toggles.clear()
        scroll_layout = self.scroll_widget.layout()

        # Clear the existing layout
        for i in reversed(range(scroll_layout.count())):
            widget = scroll_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
            else:
                # Probably the spacer/stretch item
                item = scroll_layout.itemAt(i)
                scroll_layout.removeItem(item)

        # scroll_layout = QGridLayout()
        # scroll_layout.setContentsMargins(0, 0, 0, 0)
        for calendar in calendars:
            toggle = QCheckBox(
                f"Primary ({calendar.summary})"
                if calendar.primary
                else calendar.summary
            )
            if calendar.id not in PREFERENCES.calendar_visibility:
                visibility = True
            else:
                visibility = PREFERENCES.calendar_visibility[calendar.id]

            toggle.setChecked(visibility)
            toggle.setToolTip(f"ID: {calendar.id}")
            self.calendar_toggles[calendar.id] = toggle
            scroll_layout.addWidget(toggle)
        scroll_layout.addStretch()

        # Adjust the window size if calendar # has changed
        if num_items != len(self.calendar_toggles):
            self.adjustSize()
