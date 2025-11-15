import json
import os
from datetime import datetime
from pathlib import Path

import PyQt6.QtWidgets as qtw
from PyQt6.QtGui import QCloseEvent

from .tab import Tab
from utiles import lang, utiles
from utiles.data import SESSION_EXT, SESSIONS_DIR


class MainWindow(qtw.QWidget):
    def __init__(self) -> None:
        super().__init__()
        lang.current_lang = "ru"
        self.setWindowTitle("Builder")
        self.resize(850, 720)

        self.tab_widget = qtw.QTabWidget(self)
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)

        self.btn_add = qtw.QPushButton("Add Tab")
        self.btn_add.clicked.connect(self.add_view)

        self.btn_switch = qtw.QPushButton("Switch to Next Tab")
        self.btn_switch.clicked.connect(self.switch_to_next_tab)

        self.btn_load = qtw.QPushButton("Load Session")
        self.btn_load.setMaximumWidth(100)
        self.btn_load.clicked.connect(self.choose_session)

        self.btn_save = qtw.QPushButton("Save Session")
        self.btn_save.setMaximumWidth(100)
        self.btn_save.clicked.connect(self.save_current_session)

        button_layout = qtw.QHBoxLayout()
        button_layout.addWidget(self.btn_add)
        button_layout.addWidget(self.btn_switch)
        button_layout.addWidget(self.btn_load)
        button_layout.addWidget(self.btn_save)

        main_layout = qtw.QVBoxLayout()
        main_layout.addWidget(self.tab_widget)
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

        self.tabs: list[Tab] = []

        if not self.load_last_session():
            self.add_view()

    def add_view(self):
        tab_content = Tab()
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

    def close_tab(self, index: int):
        view = self.tabs[index].automata_container.view
        if not view.is_empty():
            reply = qtw.QMessageBox.question(
                self,
                "Confirm",
                "Do you want to save automata?",
                qtw.QMessageBox.StandardButton.Yes | qtw.QMessageBox.StandardButton.No,
                qtw.QMessageBox.StandardButton.No,
            )
            if reply == qtw.QMessageBox.StandardButton.Yes:
                view.save_view()
        self.tabs.pop(index)
        self.tab_widget.removeTab(index)

    def save_current_session(self):
        try:
            session_data = []
            for tab in self.tabs:
                session_data.append(tab.dump())

            fmt_date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"{fmt_date}.{SESSION_EXT}"
            utiles.save_json(session_data, SESSIONS_DIR, filename)
        except (OSError, IOError):
            return False

        return True

    def save_session(self) -> bool:
        if all(tab.is_empty() for tab in self.tabs):
            return True

        reply = qtw.QMessageBox.question(
            self,
            "Confirm",
            "Do you want to save session?",
            qtw.QMessageBox.StandardButton.Yes | qtw.QMessageBox.StandardButton.No,
            qtw.QMessageBox.StandardButton.Yes,
        )
        if reply == qtw.QMessageBox.StandardButton.No:
            return True

        if not self.save_current_session():
            reply = qtw.QMessageBox.question(
                self,
                "Error",
                "Session doesn't saved\n Do you want to exit?",
                qtw.QMessageBox.StandardButton.Yes | qtw.QMessageBox.StandardButton.No,
                qtw.QMessageBox.StandardButton.No,
            )
            return reply != qtw.QMessageBox.StandardButton.No

        return True

    def load_last_session(self) -> bool:
        path = Path(SESSIONS_DIR)
        if not path.exists():
            os.makedirs(SESSIONS_DIR, exist_ok=True)

        sessions = [os.path.splitext(f.name) for f in path.rglob(f"*.{SESSION_EXT}")]
        if len(sessions) == 0:
            return False

        reply = qtw.QMessageBox.question(
            self,
            "Confirm",
            "Do you want to load last session?",
            qtw.QMessageBox.StandardButton.Yes | qtw.QMessageBox.StandardButton.No,
            qtw.QMessageBox.StandardButton.No,
        )
        if reply == qtw.QMessageBox.StandardButton.No:
            return False

        last_session = max(sessions, key=lambda x: x[0])
        filepath = os.path.join(SESSIONS_DIR, "".join(last_session))
        try:
            self.load_session(filepath)
        except (IOError, FileNotFoundError, json.JSONDecodeError) as ex:
            if isinstance(ex, (json.JSONDecodeError)):
                qtw.QMessageBox.warning(self, "Error", "File incorrect format")
            else:
                qtw.QMessageBox.warning(self, "Error", "Session load failed")
            while len(self.tabs) != 0:
                tab = self.tabs.pop()
                tab.deleteLater()

        return True

    def choose_session(self) -> bool:
        filepath, _ = qtw.QFileDialog.getOpenFileName(
            self, "Выберите файл", SESSIONS_DIR, "Все файлы (*.*)"
        )

        if not filepath:
            return True
        orig_len = len(self.tabs)
        try:
            self.load_session(filepath)
        except (IOError, json.JSONDecodeError, TypeError) as ex:
            if isinstance(ex, (json.JSONDecodeError, TypeError)):
                qtw.QMessageBox.warning(self, "Error", "File incorrect format")
            else:
                qtw.QMessageBox.warning(self, "Error", "Session load failed")

            while len(self.tabs) > orig_len:
                tab = self.tabs.pop()
                tab.deleteLater()
        else:
            qtw.QMessageBox.information(self, "Notification", "loaded")

        return True

    def load_session(self, session_path: str) -> Tab:
        with open(session_path, mode="r") as session_file:
            session_data = json.loads(session_file.read())
            for data in session_data:
                self.add_view()
                self.tabs[-1].load(data)

    def closeEvent(self, event: QCloseEvent | None):
        if not self.save_session():
            event.accept()
        return super().closeEvent(event)
