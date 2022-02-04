import os.path
import time

from PySide6.QtGui import *
from PySide6.QtWidgets import *


class App:
    def main(self):

        app = QApplication([])
        for i in range(5):
            app.beep()
            time.sleep(0.25)
        app.setQuitOnLastWindowClosed(False)

        # Adding an icon
        fp = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "images", "icon.png"
        )
        print("FILE PATH:", fp, os.path.exists(fp))
        icon = QIcon(fp)
        # return
        # Adding item on the menu bar
        tray = QSystemTrayIcon()
        tray.setIcon(icon)
        tray.setVisible(True)

        # Creating the options
        menu = QMenu()
        option1 = QAction("Geeks for Geeks")
        option2 = QAction("GFG")
        menu.addAction(option1)
        menu.addAction(option2)

        # To quit the app
        quit = QAction("Quit")
        quit.triggered.connect(app.quit)
        menu.addAction(quit)

        # Adding options to the System Tray
        tray.setContextMenu(menu)

        app.exec()


if __name__ == "__main__":
    app = App()
    app.main()
    print(" ALL DONE")
