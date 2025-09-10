import signal
import sys

from PyQt6.QtWidgets import QApplication
from ui.window import MainWindow
from utiles import utiles


def main():
    app = QApplication(sys.argv)

    stylesheet = utiles.load_stylesheets()

    window = MainWindow()
    window.setStyleSheet(stylesheet)

    def handle_shutdown():
        window.save_current_session()

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
