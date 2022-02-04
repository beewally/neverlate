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

from neverlate.utils import get_icon


# TODO: override the default quit (cmd + q)
class AlertDialog(QDialog):
    def __init__(self, title: str):
        super().__init__()
        self.setWindowTitle("ALERT YOU SHOULD BE SOMEWHERE")
        self.setWindowIcon(get_icon("tray_icon.png"))

        self.title = QLabel(title)
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.title)
        self.setLayout(main_layout)
        # self.setModal(True)

        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        # viewer.setWindowState( (windowState() & ~Qt::WindowMinimized) | Qt::WindowActive);
        # viewer.raise();  // for MacOS
        self.setWindowState(
            (self.windowState() & ~Qt.WindowMinimized) | Qt.WindowActive
        )
        # self.super_show()
        print("DIALOGI S SHOWN:", self.title)

        # p.communicate(b"Here are some bytes",)
        # subprocess.check_output(f"python '{p}'")
        # os.system("python '{}' &".format(p))

    def super_full_screen(self):

        screen = self.screen().geometry()
        self.setGeometry(0, 0, screen.width(), screen.height())
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.requestActivate()

    def super_show(self):
        self.show()
        # self.setFocus(True)
        self.setModal(True)
        self.showMaximized()
        self.showNormal()
        self.raise_()
        self.activateWindow()
        geo = self.geometry()
        geo.moveCenter(QCursor.pos())
        self.setGeometry(geo)
        # viewer.activateWindow(); // for Windows
        # self.setWindowFlags(Qt.FramelessWindowHint)

    # def onMouseEvent(self, *args, **kwargs):
    #    print("MOUSE", args, kwargs)
