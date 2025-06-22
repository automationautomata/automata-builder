import json
import os
from datetime import datetime

from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

import lang
import utiles
from data import SAVES_DIR, SESSION_EXT
from tab.tab import AutomataTabWidget


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

        self.tabs: list[AutomataTabWidget] = []

        # Обработчики
        self.btn_add.clicked.connect(self.add_graph_view)
        self.btn_switch.clicked.connect(self.switch_to_next_tab)
        self.load_session()

    def add_graph_view(self):
        # Создаем экземпляр нашего виджета вкладки
        tab_content = AutomataTabWidget()

        tab_name = f"View {self.tab_widget.count() + 1}"
        self.tab_widget.addTab(tab_content, tab_name)

        self.tab_widget.setCurrentWidget(tab_content)
        self.tabs.append(tab_content)

    def switch_to_next_tab(self):
        count = self.tab_widget.count()
        if count == 0:
            return

        current_index = self.tab_widget.currentIndex()
        next_index = (current_index + 1) % count
        self.tab_widget.setCurrentIndex(next_index)

    def save_session(self) -> None:
        reply = QMessageBox.question(
            self,
            "Confirm",
            "Do you want to save session?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply == QMessageBox.StandardButton.No:
            return
        
        session_data = []
        for tab in self.tabs:
            session_data.append(tab.dump())

        fmt_date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{fmt_date}.{SESSION_EXT}"
        if not utiles.json_to_file(session_data, SAVES_DIR, filename):
            reply = QMessageBox.question(
                self,
                "Error",
                "Session doesn't saved\n Do you want to exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            return reply != QMessageBox.StandardButton.No
        return True

    def load_session(self) -> None:
        sessions = [f for f in os.listdir(SAVES_DIR) if f.endswith(SESSION_EXT)]
        if len(sessions) == 0:
            return

        reply = QMessageBox.question(
            self,
            "Confirm",
            "Do you want to load last session?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.No:
            return

        last_session = sorted(s.split(".")[0] for s in sessions)[-1]
        path = os.path.join(SAVES_DIR, f"{last_session}.{SESSION_EXT}")
        with open(path, mode="r") as session_file:
            session_data = json.loads(session_file.read())
            for data in session_data:
                self.add_graph_view()
                self.tabs[-1].load(data)

    def closeEvent(self, event: QCloseEvent | None):
        if not self.save_session():
            event.accept()
        return super().closeEvent(event)
