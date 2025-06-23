import sys
from PyQt6.QtWidgets import (
    QApplication,
    QWhatsThis,
)

import utiles
from window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    QWhatsThis.enterWhatsThisMode()

    window = MainWindow()

    stylesheet = utiles.load_stylesheets()

    window.setStyleSheet(stylesheet)
    window.show()

    sys.exit(app.exec())
