import enum
import json
from typing import Callable

from PyQt6.QtCore import (
    QAbstractAnimation,
    QEasingCurve,
    QPropertyAnimation,
    QRectF,
    QSequentialAnimationGroup,
    Qt,
)
from PyQt6.QtGui import QColor, QKeyEvent
from PyQt6.QtWidgets import (
    QFileDialog,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedLayout,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from automata import Automata
from data import SAVES_DIR, VIEW_FILE_NAME
from graphics.view import AutomataGraphView
from tab.components import *  # noqa: F403
from utiles import json_to_file
from widgets import PlotWidget, VerticalMessagesWidget


class AlphabetEdit(QTextEdit):
    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.textChanged.connect(self.format_text)
        self.setPlaceholderText("{0, 1, 2, 3}")
        self.prev_text = self.toPlainText()

    def format_text(self) -> None:
        text = self.toPlainText()

        cursor = self.textCursor()
        pos = cursor.position()
        cur = text[pos - 1] if pos != 0 else pos
        new_pos = pos

        is_adding = len(text) > len(self.prev_text)

        if cur in {"\n", "\t", "\r", "{", "}"}:
            text = text.replace(cur, "")
            new_pos = pos - 1

        if not text or len(text) == 1:
            text = "{ " + text + " }"
            new_pos = len(text) - 2

        elif pos < 2 or pos > len(text) - 2:
            text = self.prev_text
            new_pos = 2 if pos < 3 else len(text) - 2

        else:
            is_insert = pos < len(text) - 2
            if cur == " " and text[pos - 2] not in ", " and is_adding:
                text = f"{text[: pos - 1]}, {text[pos:]}"
            elif cur == "," and is_adding:
                text = f"{text[:pos]} {text[pos:]}"
                pos + 1
            text = text[2:-2]

            if is_adding:
                symbols = [s.strip() for s in text.split(",") if s]
                new_pos = pos + 1 if is_insert else pos
            else:
                symbols = [s.strip() for s in text.split(",") if s.strip()]

            text = "{ " + ", ".join(dict.fromkeys(symbols)) + " }"

        self.blockSignals(True)
        self.setText(text)
        self.blockSignals(False)

        cursor.setPosition(new_pos, cursor.MoveMode.MoveAnchor)
        self.setTextCursor(cursor)

        self.prev_text = text

    def alphabet(self) -> list[str]:
        text = self.toPlainText()
        return text[2:-2].split(", ") if text else []


class AutomataDataWidget(QWidget):
    def __init__(
        self,
        parent: QWidget | None = None,
        alphabet_item_height: int = 60,
        initial_state_height: int = 40,
    ) -> None:
        super().__init__(parent)
        self.input_alphabet_field = AlphabetEdit(parent=self)
        self.input_alphabet_field.setMinimumHeight(alphabet_item_height)

        self.output_alphabet_field = AlphabetEdit(parent=self)
        self.output_alphabet_field.setMinimumHeight(alphabet_item_height)

        self.initial_state_field = QTextEdit(self)
        self.initial_state_field.setMinimumHeight(initial_state_height)
        self.initial_state_field.setPlaceholderText("initial state")
        self.initial_state_field.textChanged.connect(self.filter_initial_state_input)

        self.verify_button = QPushButton("Verify")
        self.draw_button = QPushButton("Draw")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        layout.setSpacing(4)
        layout.addWidget(QLabel("Input alphabet"))
        layout.addWidget(self.input_alphabet_field)

        layout.addSpacing(alphabet_item_height // 3)
        layout.addWidget(QLabel("Output alphabet"))
        layout.addWidget(self.output_alphabet_field)

        layout.addSpacing(alphabet_item_height // 3)
        layout.addWidget(QLabel("Initial state"))
        layout.addWidget(self.initial_state_field)

        layout.addSpacing(initial_state_height // 3)
        layout.addWidget(self.verify_button)
        layout.addWidget(self.draw_button)

    def filter_initial_state_input(self) -> None:
        text_edit = self.initial_state_field
        text = text_edit.toPlainText()
        filtered_text = "".join(s for s in text if s not in "\r\t\n ")
        if filtered_text == text:
            return

        text_edit.blockSignals(True)
        text_edit.setText(filtered_text)
        text_edit.blockSignals(False)

        cursor = text_edit.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        text_edit.setTextCursor(cursor)

    def input_alphabet(self) -> list[str]:
        return self.input_alphabet_field.alphabet()

    def output_alphabet(self) -> list[str]:
        return self.output_alphabet_field.alphabet()

    def initial_state(self) -> str:
        return self.initial_state_field.toPlainText()

    def set_data(
        self, input_alphabet: list[str], output_alphabet: list[str], initial_state: str
    ) -> None:
        self.input_alphabet_field.setText("{" + ", ".join(input_alphabet) + "}")
        self.output_alphabet_field.setText("{" + ", ".join(output_alphabet) + "}")
        self.initial_state_field.setText(initial_state)


class SidePanel(QWidget):
    class Mode(enum.Enum):
        ERROR_MESSAGES = enum.auto()
        PLOT = enum.auto()
        EMPTY = enum.auto()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.cur_mode_ = self.Mode.EMPTY

        self.container = QWidget(self)
        self.container.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        self.error_messages = VerticalMessagesWidget()
        self.error_messages.setContentsMargins(0, 0, 0, 0)
        self.error_messages.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        self.plot = PlotWidget()
        self.plot.setContentsMargins(0, 0, 0, 0)
        self.plot.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        self.stack_layout = QStackedLayout()
        self.stack_layout.addWidget(self.error_messages)
        self.stack_layout.addWidget(self.plot)

        self.close_button = QPushButton(">>")

        self.main_layout = QVBoxLayout(self.container)
        self.main_layout.addLayout(self.stack_layout)
        self.main_layout.addWidget(self.close_button)

    def resizeEvent(self, a0) -> None:
        self.blockSignals(True)
        self.container.resize(self.size())
        self.blockSignals(False)
        return super().resizeEvent(a0)

    @property
    def current_mode(self) -> "SidePanel.Mode":
        return self.cur_mode_

    def set_mode(self, mode: Mode) -> None:
        if mode == self.Mode.ERROR_MESSAGES:
            self.stack_layout.setCurrentWidget(self.error_messages)
            self.cur_mode_ = self.Mode.ERROR_MESSAGES

        elif mode == self.Mode.PLOT:
            self.stack_layout.setCurrentWidget(self.plot)
            self.cur_mode_ = self.Mode.ERROR_MESSAGES

        elif mode == self.Mode.EMPTY:
            self.stack_layout.setCurrentWidget(None)
            self.cur_mode_ = self.Mode.EMPTY

    def add_messages(self, *messages: str) -> None:
        if self.current_mode != self.Mode.ERROR_MESSAGES:
            raise Exception("Error messages widget doesn't set")

        group = QSequentialAnimationGroup(self.error_messages)

        pause = 120
        for msg in messages:
            self.error_messages.add_message(msg)
            last = self.error_messages.count() - 1
            label = self.error_messages.get_message(last)

            opacity_effect = QGraphicsOpacityEffect(label)
            opacity_effect.setOpacity(0)
            label.setGraphicsEffect(opacity_effect)

            animation = QPropertyAnimation(
                opacity_effect, b"opacity", self.error_messages
            )
            animation.setDuration(400)
            animation.setStartValue(0)
            animation.setEndValue(1)
            animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

            group.addAnimation(animation)
            group.addPause(pause)

        group.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)

    def clear_messages(self) -> None:
        if self.current_mode != self.Mode.ERROR_MESSAGES:
            raise Exception("Error messages widget doesn't set")
        self.error_messages.clear()

    def draw_plot(self, x: list[int], y: list[int]) -> None:
        if self.current_mode != self.Mode.ERROR_MESSAGES:
            raise Exception("Plot widget doesn't set")

        self.plot.draw(x, y)

    def switch_to_plot(self) -> None:
        if self.current_mode == self.Mode.PLOT:
            raise Exception("Plot widget is already setted")
        self.set_mode(self.Mode.PLOT)

    def switch_to_messages(self) -> None:
        if self.current_mode == self.Mode.ERROR_MESSAGES:
            raise Exception("Error messages widget is already setted")

        self.set_mode(self.Mode.ERROR_MESSAGES)
        # self.error_messages.setMaximumSize(self.size())

    def switch_to_empty(self) -> None:
        self.set_mode(self.Mode.EMPTY)


class AutomataWordInput(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.input_word_edit = QLineEdit()
        self.input_word_edit.setPlaceholderText("Input word")
        self.input_word_edit.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

        self.output_word_edit = QLineEdit()
        self.output_word_edit.setPlaceholderText("Output word")
        self.output_word_edit.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

        layout = QVBoxLayout()
        layout.addWidget(self.input_word_edit)
        layout.addWidget(self.output_word_edit)

        self.forward_button = QPushButton(text=">")
        self.forward_button.setContentsMargins(0, 0, 0, 0)

        self.backword_button = QPushButton(text="<")
        self.backword_button.setContentsMargins(0, 0, 0, 0)

        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.addWidget(self.backword_button)
        buttons_layout.addWidget(self.forward_button)

        main_layout = QHBoxLayout()
        main_layout.addLayout(layout)
        main_layout.addLayout(buttons_layout)
        main_layout.setAlignment(buttons_layout, Qt.AlignmentFlag.AlignTop)

        self.setLayout(main_layout)
        self.setContentsMargins(0, 0, 0, 0)

    @property
    def input_word(self) -> str:
        return self.input_word_edit.text()

    @input_word.setter
    def input_word(self, value: str) -> str:
        return self.input_word_edit.setText(value)

    @property
    def output_word(self) -> str:
        return self.output_word_edit.text()

    @output_word.setter
    def output_word(self, value: str) -> None:
        self.output_word_edit.setText(value)

    def append_to_output(self, value: str) -> None:
        output_word = f"{self.output_word}{value}"
        self.output_word_edit.setText(output_word)


class AutomataContainer(QWidget):
    def __init__(
        self,
        parent: QWidget | None = None,
        button_size: int = 55,
        tact_counter_size: int = 100,
    ) -> None:
        super().__init__(parent)
        self.view = AutomataGraphView()
        self.view.fitInView(
            QRectF(0, 0, self.height() * 0.9, self.width() * 0.9),
            Qt.AspectRatioMode.KeepAspectRatio,
        )
        self.view.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        self.word_input = AutomataWordInput()
        self.word_input.setMinimumHeight(self.height() // 6)
        self.word_input.setMaximumWidth(self.width())
        self.word_input.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.word_input.input_word_edit.textChanged.connect(self.filter_input)
        self.word_input.forward_button.clicked.connect(self.forward_click)
        self.word_input.backword_button.clicked.connect(self.backward_click)

        automata_layout = QVBoxLayout(self)
        automata_layout.addWidget(self.view)
        automata_layout.addWidget(self.word_input, 0, Qt.AlignmentFlag.AlignTop)

        # --------------------------------------
        # self.overlay_container = QWidget(self.view)
        # self.overlay_container.setFixedSize(self.view.size())

        # # self.overlay_container.setContentsMargins(6, 7, 0, 0)
        # self.overlay_container.setAttribute(
        #     Qt.WidgetAttribute.WA_TransparentForMouseEvents, False
        # )
        # self.overlay_container.setAttribute(
        #     Qt.WidgetAttribute.WA_NoSystemBackground, True
        # )
        # self.overlay_container.setAttribute(
        #     Qt.WidgetAttribute.WA_TranslucentBackground, True
        # )

        # self.save_button = QPushButton("Save")
        # self.save_button.setFixedSize(button_size, button_size//2)
        # self.save_button.clicked.connect(self.save_view)

        # self.load_button = QPushButton("Load")
        # self.load_button.setFixedSize(button_size, button_size//2)
        # self.load_button.clicked.connect(self.load_view)

        # buttons_layout = QHBoxLayout()
        # buttons_layout.addWidget(self.load_button)
        # buttons_layout.addWidget(self.save_button)

        # self.tact_counter = QLabel('145235')
        # self.tact_counter.setContentsMargins(0, 0, 0, 0)
        # self.tact_counter.setFixedSize(tact_counter_size, tact_counter_size)

        # # --------------------------------------
        # overlay_layout = QVBoxLayout(self.overlay_container)
        # overlay_layout.addLayout(buttons_layout)
        # buttons_layout.addStretch(2)
        # overlay_layout.addWidget(self.tact_counter, 2, Qt.AlignmentFlag.AlignBottom)
        # self.overlay_container.setLayout(overlay_layout)

        # --------------------------------------
        self.prev_input_word = self.word_input.input_word
        self.transitions_history = []
        self.automata_check = None

    def set_automata_check(self, automata_check: Callable[[Automata], bool]) -> None:
        self.automata_check = automata_check

    def automata(self) -> Automata:
        return self.view.to_automata()

    def filter_input(self) -> None:
        word = self.word_input.input_word
        input_alphabet = self.automata().input_alphabet
        if all(s in input_alphabet for s in word):
            self.prev_input_word = word
            return
        self.word_input.blockSignals(True)
        self.word_input.input_word = self.prev_input_word
        self.word_input.blockSignals(False)
        QMessageBox.warning(self, "Error", "Invalid input symbol")

    def forward_click(self) -> None:
        if not (self.word_input.input_word and self.automata_check):
            return

        automata = self.automata()
        if not self.automata_check(automata):
            return

        n = len(self.word_input.output_word)
        if n == len(self.word_input.input_word):
            return

        if n == 0:
            self.transitions_history.clear()
            self.transitions_history.append(automata.initial_state)

        cur_state = self.transitions_history[-1]
        cur_symb = self.word_input.input_word[n]
        state, out_ = automata.transition(cur_symb, cur_state)

        self.word_input.append_to_output(out_)
        self.view.mark_node(state, QColor(128, 0, 0))
        self.transitions_history.append(state)

    def backward_click(self) -> None:
        if not (self.word_input.input_word and self.automata_check):
            return

        if len(self.transitions_history) == 0:
            return

        # Reduce on 1 symbol output word
        output_word = self.word_input.output_word
        self.word_input.output_word = output_word[:-1]

        # Mark previous state
        state = self.transitions_history.pop()
        self.view.unmark_node(state)

    def keyPressEvent(self, event: QKeyEvent | None) -> None:
        is_s_key = event.key() == Qt.Key.Key_S
        is_cntrl_modifier = event.modifiers() == Qt.KeyboardModifier.ControlModifier

        if is_cntrl_modifier and is_s_key:
            self.save_view()

        return super().keyPressEvent(event)

    def save_view(self) -> None:
        reply = QMessageBox.question(
            self,
            "Confirm",
            "Do you want to save?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.No:
            return

        if json_to_file(self.view.serialize(), SAVES_DIR, VIEW_FILE_NAME):
            QMessageBox.information(self, "Notification", "saved")
            return

        QMessageBox.warning(self, "Error", "Automata save failed")

    def load_view(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл", SAVES_DIR, "Все файлы (*.*)"
        )

        if not file_path:
            return

        try:
            self.view.clear_scene()
            with open(file_path, mode="r") as file:
                self.view.deserialize(file.read())
        except IOError:
            QMessageBox.warning(self, "Error", "Automata save failed")
        except (json.JSONDecodeError, TypeError):
            QMessageBox.warning(self, "Error", "File incorrect format")
        else:
            QMessageBox.information(self, "Notification", "loaded")
