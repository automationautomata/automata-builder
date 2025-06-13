import enum
import math
from typing import Any, Callable

from PyQt6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    Qt,
    QSequentialAnimationGroup, QParallelAnimationGroup, QAbstractAnimation, QRect
)
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QGraphicsOpacityEffect,
)

from graphics import AutomataGraphView
from tools.widgets import VerticalMessagesWidget


class AlphabetEdit(QTextEdit):
    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.textChanged.connect(self.format_text)
        self.setPlaceholderText("{0, 1, ..., 3} = {0, 1, 2, 3}")
        self.prev_text = ""

    def format_text(self) -> None:
        text = self.toPlainText()

        cursor = self.textCursor()
        pos = cursor.position()
        cur = text[pos - 1]
        new_pos = pos

        if cur in "\n\t\r{}" and 3 < pos > len(self.prev_text) - 2:
            text = f"{text[: pos - 1]}{text[pos]}"
            new_pos = pos - 1

        if not text or len(text) == 1:
            text = "{ " + text + " }"
            new_pos = len(text) - 2

        elif pos < 2 or pos > len(text) - 2:
            text = self.prev_text
            new_pos = 2 if pos < 3 else len(text) - 2

        else:
            if cur == " " and text[pos - 2] not in ", ":
                text = f"{text[: pos - 1]}, {text[pos:]}"

            text = text[2:-2]
            symbols = [s.strip() for s in text.split(",") if s]
            text = "{ " + ", ".join(dict.fromkeys(symbols)) + " }"
            if pos != len(text) - 2:
                new_pos = pos + 1
            else:
                pos += 1
        # Block signals temporarily to prevent recursion

        self.blockSignals(True)
        self.setText(text)
        self.blockSignals(False)

        cursor.setPosition(new_pos, cursor.MoveMode.MoveAnchor)
        self.setTextCursor(cursor)

        self.prev_text = text


class AutomataDataWidget(QWidget):
    def __init__(
        self, parent: QWidget | None = None, edit_item_height: int = 60
    ) -> None:
        super().__init__(parent)
        self.input_alphabet_title = QLabel("Input alphabet", self)
        self.output_alphabet_title = QLabel("Output alphabet", self)
        self.initial_state_title = QLabel("Initial state", self)

        self.input_alphabet_field = AlphabetEdit(parent=self)
        self.output_alphabet_field = AlphabetEdit(parent=self)
        self.initial_state_field = QTextEdit(self)

        self.verify_button = QPushButton("Verify", self)

        self.input_alphabet_field.setFixedHeight(edit_item_height)
        self.output_alphabet_field.setFixedHeight(edit_item_height)

        self.initial_state_field.setPlaceholderText("initial state")

        text_layout = QVBoxLayout(self)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        text_layout.setSpacing(4)
        text_layout.addWidget(self.input_alphabet_title)
        text_layout.addWidget(self.input_alphabet_field)

        text_layout.addSpacing(edit_item_height // 3)
        text_layout.addWidget(self.output_alphabet_title)
        text_layout.addWidget(self.output_alphabet_field)

        text_layout.addSpacing(edit_item_height // 3)
        text_layout.addWidget(self.initial_state_title)
        text_layout.addWidget(self.initial_state_field)

        text_layout.addSpacing(edit_item_height // 3)
        text_layout.addWidget(self.verify_button)

    def input_alphabet(self):
        return self.input_alphabet_field.toPlainText()[2:-2].split(", ")

    def output_alphabet(self):
        return self.output_alphabet_field.toPlainText()[2:-2].split(", ")


class SidePanel(QWidget):
    class Mode(enum.Enum):
        ERROR_MESSAGES = enum.auto()
        PLOT = enum.auto()
        EMPTY = enum.auto()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.error_messages: VerticalMessagesWidget = None
        self.plot: None = None
        self.cur_mode_ = self.Mode.EMPTY
        self.button = QPushButton(self)

    @property
    def current_mode(self):
        return self.cur_mode_

    def set_mode(self, mode: Mode):
        fields = self.__dict__.keys() - self.__class__.__dict__.keys()

        if mode == self.Mode.ERROR_MESSAGES:
            for field_name in fields:
                value = getattr(self, field_name)
                if isinstance(value, QWidget) and not isinstance(
                    value, (VerticalMessagesWidget, QPushButton)
                ):
                    setattr(self, field_name, None)
                    value.deleteLater()
            self.cur_mode_ = self.Mode.ERROR_MESSAGES
            return

        if mode == self.Mode.EMPTY:
            for field_name in fields:
                value = getattr(self, field_name)
                if isinstance(value, QWidget):
                    setattr(self, field_name, None)
                    value.deleteLater()
            self.cur_mode_ = self.Mode.EMPTY
            return

    def add_messages(self, *messages: tuple[str]):
        if self.current_mode != self.Mode.ERROR_MESSAGES:
            raise Exception("Error messages widget doesn't enabled")
        group = QSequentialAnimationGroup(self.error_messages)

        pause = 120
        for msg in messages:
            self.error_messages.add_message(msg)
            last = self.error_messages.count - 1
            label = self.error_messages.get_message(last)
            label.setMinimumWidth(self.width())

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

    def claer_messages(self):
        if self.current_mode != self.Mode.ERROR_MESSAGES:
            raise Exception("Error messages widget doesn't enabled")
        self.error_messages.clear()

    def enable_error_messages(self, *messages: tuple[str]):
        if self.current_mode == self.Mode.ERROR_MESSAGES:
            raise Exception("Error messages widget is already enabled")
        self.set_mode(self.Mode.ERROR_MESSAGES)
        self.error_messages = VerticalMessagesWidget(self, *messages)

        self.error_messages.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.error_messages.setFixedWidth(self.maximumWidth())
        self.error_messages.setFixedHeight(self.height())

    def enable_plot(self):
        if self.current_mode == self.Mode.PLOT:
            raise Exception("Plot widget is already enabled")
        self.set_mode(self.Mode.PLOT)

    def show(self):
        super().show()
        fields = self.__dict__.keys() - self.__class__.__dict__.keys()
        for field_name in fields:
            value = getattr(self, field_name)
            if isinstance(value, QWidget):
                value.show()

    def disable(self):
        self.set_mode(self.Mode.EMPTY)


class AutomataTabWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.view = AutomataGraphView(self)
        self.view.setMinimumSize(self.width() // 4, self.height() // 3)

        self.automata_data = AutomataDataWidget(self)
        self.automata_data.setMinimumHeight(2 * self.height() // 3)
        self.automata_data.setMaximumWidth(self.width() // 3)

        self.hidden_panel = SidePanel(self)
        self.hidden_panel.setMinimumHeight(self.height())
        self.hidden_panel.setMaximumWidth(self.width() // 3)

        general_layout = QHBoxLayout(self)

        general_layout.addWidget(self.view)
        general_layout.addWidget(self.automata_data, 0, Qt.AlignmentFlag.AlignTop)
        general_layout.addWidget(self.hidden_panel)

        self.automata_data.verify_button.clicked.connect(self.verify_button_click)

    def verify_button_click(self) -> None:
        errors = ["ERRORERRORERRORERRORERRORERRORERROR", "2, 3"]

        if self.hidden_panel.current_mode == SidePanel.Mode.ERROR_MESSAGES:
            self.hidden_panel.add_messages(*errors)
            print(self.hidden_panel.error_messages.size())
            l = self.hidden_panel.error_messages.labels_
            print(" ".join(str(x.width()) for x in l))
            print()
        else:
            self.hidden_panel.enable_error_messages()
            self.hidden_panel.show()
            self.layout().setEnabled(False)
            def after_finish():
                l = self.hidden_panel.error_messages.labels_
                print(" ".join(str(x.width()) for x in l))
                self.hidden_panel.add_messages(*errors)
                self.layout().setEnabled(True)

            self.toggle_panel(after_finish)
            self.hidden_panel.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )

    def toggle_panel(self, after_finish: Callable[[Any], None] | None = None) -> None:
        print("Hello", self.hidden_panel.width())
        duration = 500
        width = self.hidden_panel.maximumWidth()
        

        anim_panel = QPropertyAnimation(self.hidden_panel, b"geometry", self)
        anim_panel.setStartValue(self.hidden_panel.geometry())

        panel_dest_geometry = self.hidden_panel.geometry()

        if self.hidden_panel.width() == 0:
            panel_dest_geometry.setLeft(panel_dest_geometry.left() - width)
            panel_dest_geometry.setWidth(width)
        else:
            panel_dest_geometry.setLeft(panel_dest_geometry.left() + width)
            panel_dest_geometry.setWidth(0)

        anim_panel.setEndValue(panel_dest_geometry)
        
        anim_panel.setDuration(duration)
        anim_panel.setEasingCurve(QEasingCurve.Type.InOutQuad)

        if after_finish:
            anim_panel.finished.connect(after_finish)

        anim_panel.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
