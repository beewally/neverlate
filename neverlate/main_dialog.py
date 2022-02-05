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
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from neverlate.utils import get_icon, now_datetime, pretty_datetime

if typing.TYPE_CHECKING:
    from neverlate.event_alerter import EventAlerter

# Table columns
TABLE_SUMMARY = 0
TABLE_TIME_TILL_ALERT = 1
TABLE_EVENT_TIMES = 2
TABLE_CALENDAR = 3


# Colors
BLACK = QColor(*(3 * [0]))
DARK_GREY = QColor(*(3 * [50]))
LIGHT_GREY = QColor(*(3 * [200]))
LIGHT_GREEN = QColor(200, 255, 200)
LIGHT_RED = QColor(255, 200, 200)
LIGHT_YELLOW = QColor(255, 255, 200)
WHITE = QColor(*(3 * [255]))


class TimeTillAlertWidget(QWidget):
    """Widget to show some the time till an event (4:32) and a button to re-trigger teh alert."""

    def __init__(self, text: str):
        super().__init__()

        box_layout = QHBoxLayout()
        box_layout.setContentsMargins(0, 0, 0, 0)
        self.main_text = QLabel(text)
        self.reset_button = QPushButton(icon=get_icon("alarm.png"))
        box_layout.addWidget(self.main_text)
        box_layout.addWidget(self.reset_button)
        self.setLayout(box_layout)


class MainDialog(QDialog):
    """Main dialog to show general info."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("NeverLate")
        # self.setWindowFlags(
        #     Qt.Tool
        # )  # TODO: test / research more https://doc.qt.io/qt-5/qt.html#WindowType-enum
        self.setWindowIcon(get_icon("tray_icon.png"))
        self.update_now_button = QPushButton("Update Now")
        self.quit_button = QPushButton("Exit App")
        self.time_to_update_label = QLabel()

        self.event_table = QTableWidget(0, 4)
        self.event_table.setHorizontalHeaderItem(
            TABLE_SUMMARY, QTableWidgetItem("Event")
        )
        self.event_table.setHorizontalHeaderItem(
            TABLE_EVENT_TIMES, QTableWidgetItem("Time")
        )
        self.event_table.setHorizontalHeaderItem(
            TABLE_TIME_TILL_ALERT, QTableWidgetItem("Tim Till Alert")
        )
        self.event_table.setHorizontalHeaderItem(
            TABLE_CALENDAR, QTableWidgetItem("Calendar")
        )
        # self.event_table.horizontalHeader().hide()
        self.event_table.verticalHeader().hide()
        self.event_table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.event_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        self.event_table.horizontalHeader().setStretchLastSection(True)
        self.event_table.setEditTriggers(QTableWidget.NoEditTriggers)
        # table->horizontalHeader()->setSectionResizeMode(QHeaderView::Stretch);

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.event_table)
        # main_layout.addStretch()

        layout = QHBoxLayout()
        layout.addStretch()
        layout.addWidget(self.time_to_update_label)
        layout.addWidget(self.update_now_button)

        main_layout.addLayout(layout)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.quit_button)
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

    def update_table_with_events(self, alerters: list[EventAlerter]):
        """Update the table with the specified alerter events."""
        # TODO: break this function up
        orig_row_count = self.event_table.rowCount()
        self.event_table.setRowCount(len(alerters))
        alerters.sort(key=lambda a: a.time_event.start_time)
        now = now_datetime()
        for idx, alerter in enumerate(alerters):
            # font = item.font()  # type: QFont
            # font.setStrikeOut(True)
            # item.setFont(font)

            self.event_table.setItem(
                idx, TABLE_SUMMARY, QTableWidgetItem(alerter.time_event.summary)
            )

            # Start time
            start_label = pretty_datetime(alerter.time_event.start_time).split()[0]
            end_label = pretty_datetime(alerter.time_event.end_time)
            self.event_table.setItem(
                idx,
                TABLE_EVENT_TIMES,
                QTableWidgetItem(f"{start_label} - {end_label}"),
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

            if alerter.has_alerted:
                # Show the dialog WITH a button to reset the alert.
                self.event_table.setItem(idx, TABLE_TIME_TILL_ALERT, None)  # type: ignore
                time_till_widget = TimeTillAlertWidget(time_till_alert)
                time_till_widget.reset_button.clicked.connect(alerter.reset_alert)
                self.event_table.setCellWidget(
                    idx, TABLE_TIME_TILL_ALERT, time_till_widget
                )

            else:
                # Set the base text
                self.event_table.setItem(
                    idx, TABLE_TIME_TILL_ALERT, QTableWidgetItem(time_till_alert)
                )
                self.event_table.setCellWidget(idx, TABLE_TIME_TILL_ALERT, None)

            # Calendar
            self.event_table.setItem(
                idx,
                TABLE_CALENDAR,
                QTableWidgetItem(alerter.time_event.calendar.summary),
            )

            # =================== Styles =====================
            if alerter.time_event.has_declined():
                # User declined. Set strikethrough font & italic
                # for column in range(self.event_table.columnCount()):
                item = self.event_table.item(idx, TABLE_SUMMARY)
                font = QFont()
                font.setItalic(True)
                font.setStrikeOut(True)
                item.setFont(font)
            if now > alerter.time_event.end_time:
                # Meeting is over. 'Disable' it.
                for column in range(self.event_table.columnCount()):
                    item = self.event_table.item(idx, column)
                    if not item:
                        continue
                    background = item.background()
                    background.setColor(LIGHT_GREY)
                    foreground = item.foreground()
                    foreground.setColor(DARK_GREY)
                    background.setStyle(Qt.BrushStyle.SolidPattern)
                    foreground.setStyle(Qt.BrushStyle.SolidPattern)
                    item.setBackground(background)
                    item.setForeground(foreground)
            elif alerter.time_event.start_time < now < alerter.time_event.end_time:
                # Meeting is happening
                for column in range(self.event_table.columnCount()):
                    if alerter.dismissed_alerts:  # User is in the meeting (in theory)
                        bg_color = LIGHT_GREEN  # Light green
                    else:  # User should be in th emeeting
                        bg_color = LIGHT_RED
                    item = self.event_table.item(idx, column)
                    widget = self.event_table.cellWidget(idx, column)

                    if not item:
                        palette = widget.palette()
                        widget.setPalette(palette)
                        widget.setAttribute(Qt.WA_StyledBackground, True)
                        widget.setStyleSheet(
                            f"background-color: rgb({bg_color.red()}, {bg_color.green()}, {bg_color.blue()});"
                        )
                        palette.setColor(widget.backgroundRole(), bg_color)
                        continue
                    background = item.background()
                    foreground = item.foreground()
                    foreground.setColor(BLACK)
                    background.setColor(bg_color)
                    background.setStyle(Qt.BrushStyle.SolidPattern)
                    foreground.setStyle(Qt.BrushStyle.SolidPattern)
                    item.setBackground(background)
                    item.setForeground(foreground)
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
            elif now + timedelta(minutes=30) > alerter.time_event.start_time:
                # Meeting is coming up soon
                for column in range(self.event_table.columnCount()):
                    item = self.event_table.item(idx, column)
                    if not item:
                        continue
                    background = item.background()
                    background.setColor(LIGHT_YELLOW)
                    foreground = item.foreground()
                    foreground.setColor(BLACK)
                    background.setStyle(Qt.BrushStyle.SolidPattern)
                    foreground.setStyle(Qt.BrushStyle.SolidPattern)
                    item.setBackground(background)
                    item.setForeground(foreground)
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
            else:
                # Future event
                for column in range(self.event_table.columnCount()):
                    item = self.event_table.item(idx, column)
                    if not item:
                        continue
                    background = item.background()
                    background.setColor(WHITE)
                    foreground = item.foreground()
                    foreground.setColor(BLACK)
                    background.setStyle(Qt.BrushStyle.SolidPattern)
                    foreground.setStyle(Qt.BrushStyle.SolidPattern)
                    item.setBackground(background)
                    item.setForeground(foreground)
                    font = item.font()
                    item.setFont(font)

        # self.event_table.resizeColumnsToContents()
        if orig_row_count != len(alerters):
            self.adjustSize()
