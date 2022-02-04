"""Main app entry point."""


from PySide6.QtWidgets import (
    QDialog,  # pylint: disable=no-name-in-module
    QPushButton,
    QVBoxLayout,
)

from neverlate.utils import get_icon

# TODO: implement


class PreferencesDialog(QDialog):  # pylint: disable=too-few-public-methods
    """Preferences dialog panes"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setWindowTitle("Preferences")
        self.setWindowIcon(get_icon("tray_icon.png"))
        self.quit_button = QPushButton("Press to quit")
        # self.button.clicked.connect(close_s)

        layout = QVBoxLayout()
        layout.addStretch()
        layout.addWidget(self.quit_button)
        self.setLayout(layout)
