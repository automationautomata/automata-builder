import signal
import sys

from PyQt6.QtWidgets import QApplication

from automata_builder.core.utiles import utiles
from automata_builder.core.window import MainWindow


def main():
    app = QApplication(sys.argv)
    # QWhatsThis.enterWhatsThisMode()
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
