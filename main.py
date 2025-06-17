import sys

from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QWhatsThis,
)

import lang
from tab import AutomataTabWidget
from tools import utiles


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        lang.current_lang = "ru"
        self.setWindowTitle("QTabWidget с QGraphicsView")
        self.resize(850, 720)

        main_layout = QVBoxLayout(self)
        self.setLayout(main_layout)

        # Создаем QTabWidget
        self.tab_widget = QTabWidget(self)
        main_layout.addWidget(self.tab_widget)

        # Создаем кнопки
        button_layout = QHBoxLayout(self)
        self.btn_add = QPushButton("Add AutomataGraphView", self)
        self.btn_switch = QPushButton("Switch to Next Tab", self)

        button_layout.addWidget(self.btn_add)
        button_layout.addWidget(self.btn_switch)
        main_layout.addLayout(button_layout)

        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()  # чтобы сдвинуть кнопку вправо
        self.errors_button = QPushButton(self)
        bottom_layout.addWidget(self.errors_button)
        main_layout.addLayout(bottom_layout)

        # Обработчики
        self.btn_add.clicked.connect(self.add_graph_view)
        self.btn_switch.clicked.connect(self.switch_to_next_tab)

    def add_graph_view(self):
        # Создаем экземпляр нашего виджета вкладки
        tab_content = AutomataTabWidget()

        # Добавляем его как новую вкладку
        tab_name = f"View {self.tab_widget.count() + 1}"
        self.tab_widget.addTab(tab_content, tab_name)

        # Переключаемся на новую вкладку
        self.tab_widget.setCurrentWidget(tab_content)

    def switch_to_next_tab(self):
        count = self.tab_widget.count()
        if count == 0:
            return

        current_index = self.tab_widget.currentIndex()
        next_index = (current_index + 1) % count
        self.tab_widget.setCurrentIndex(next_index)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()

    stylesheet = utiles.load_stylesheets()

    window.setStyleSheet(stylesheet)
    window.show()
    QWhatsThis.enterWhatsThisMode()

    sys.exit(app.exec())
