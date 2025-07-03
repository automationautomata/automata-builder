import sys

from PyQt6.QtWidgets import QApplication, QWhatsThis

from .core.utiles import utiles
from .core.window import MainWindow


def main():
    app = QApplication(sys.argv)
    # QWhatsThis.enterWhatsThisMode()
    stylesheet = utiles.load_stylesheets()

    window = MainWindow()
    window.setStyleSheet(stylesheet)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
