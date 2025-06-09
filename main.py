import sys

from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import lang
from graphics import AutomataGraphView


class TabWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.view = AutomataGraphView(self)

        self.side_widgets = QWidget()
        self.side_widgets.setFixedHeight(200)

        self.input_alphabet_title = QLabel("Input alphabet", self)
        self.output_alphabet_title = QLabel("Output alphabet", self)
        self.initial_state_title = QLabel("Initial state", self)

        self.input_alphabet_enter = QTextEdit(self)
        self.output_alphabet_enter = QTextEdit(self)
        self.initial_state_enter = QTextEdit(self)

        self.verify_button = QPushButton("Verify", self)

        self.input_alphabet_enter.setPlaceholderText("{0, 1, ..., 3} = {0, 1, 2, 3}")
        self.output_alphabet_enter.setPlaceholderText("{0, 1, ..., 3} = {0, 1, 2, 3}")
        self.initial_state_enter.setPlaceholderText("initial state")

        text_layout = QVBoxLayout()
        self.side_widgets.setLayout(text_layout)

        text_layout.setSpacing(5)
        text_layout.addWidget(self.input_alphabet_title)
        text_layout.addWidget(self.input_alphabet_enter)

        text_layout.addWidget(self.output_alphabet_title)
        text_layout.addWidget(self.output_alphabet_enter)

        text_layout.addWidget(self.initial_state_title)
        text_layout.addWidget(self.initial_state_enter)

        text_layout.addWidget(self.verify_button)

        general_layout = QHBoxLayout()
        general_layout.addStretch(1)
        general_layout.addWidget(self.view)
        general_layout.addWidget(self.side_widgets)

        self.setLayout(general_layout)

    def verify_button_click(self):
        automata = self.view.to_automata()
        if automata.verify():
            msg = "Automata is correct"
        else:
            msg = "Automata isn't correct"
        QMessageBox.warning(msg)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        lang.current_lang = "ru"
        self.setWindowTitle("QTabWidget с QGraphicsView")
        self.resize(800, 600)

        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # Создаем QTabWidget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # Создаем кнопки
        button_layout = QHBoxLayout()
        self.btn_add = QPushButton("Add AutomataGraphView")
        self.btn_switch = QPushButton("Switch to Next Tab")
        button_layout.addWidget(self.btn_add)
        button_layout.addWidget(self.btn_switch)
        main_layout.addLayout(button_layout)

        # Обработчики
        self.btn_add.clicked.connect(self.add_graph_view)
        self.btn_switch.clicked.connect(self.switch_to_next_tab)

    def add_graph_view(self):
        # Создаем экземпляр нашего виджета вкладки
        tab_content = TabWidget()

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
    window.show()
    sys.exit(app.exec())
