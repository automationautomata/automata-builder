import enum
from itertools import permutations
from typing import Callable

from PyQt6.QtCore import (
    QAbstractAnimation,
    QEasingCurve,
    QPropertyAnimation,
    QRect,
    QSequentialAnimationGroup,
    Qt,
)
from PyQt6.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStackedLayout,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from automata import Automata
from graphics import AutomataGraphView
from tools.widgets import PlotWidget, VerticalMessagesWidget


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
        return self.toPlainText()[2:-2].split(", ")


class AutomataDataWidget(QWidget):
    def __init__(
        self,
        parent: QWidget | None = None,
        alphabet_item_height: int = 60,
        initial_state_height: int = 40,
    ) -> None:
        super().__init__(parent)
        self.input_alphabet_title = QLabel("Input alphabet", self)
        self.output_alphabet_title = QLabel("Output alphabet", self)
        self.initial_state_title = QLabel("Initial state", self)

        self.input_alphabet_field = AlphabetEdit(parent=self)
        self.input_alphabet_field.setMaximumHeight(alphabet_item_height)

        self.output_alphabet_field = AlphabetEdit(parent=self)
        self.output_alphabet_field.setMaximumHeight(alphabet_item_height)

        self.initial_state_field = QTextEdit(self)
        self.initial_state_field.setPlaceholderText("initial state")
        self.initial_state_field.textChanged.connect(self.filter_initial_state_input)

        self.verify_button = QPushButton("Verify")
        self.draw_button = QPushButton("Draw")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        layout.setSpacing(4)
        layout.addWidget(self.input_alphabet_title)
        layout.addWidget(self.input_alphabet_field)

        layout.addSpacing(alphabet_item_height // 3)
        layout.addWidget(self.output_alphabet_title)
        layout.addWidget(self.output_alphabet_field)

        layout.addSpacing(alphabet_item_height // 3)
        layout.addWidget(self.initial_state_title)
        layout.addWidget(self.initial_state_field)

        layout.addSpacing(initial_state_height // 3)
        layout.addWidget(self.verify_button)
        layout.addWidget(self.draw_button)

    def filter_initial_state_input(self):
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

    def initial_state(self):
        return self.initial_state_field.toPlainText()


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

        group = QSequentialAnimationGroup(self.error_messages.container)

        pause = 120
        for msg in messages:
            self.error_messages.add_message(msg)
            last = self.error_messages.count - 1
            label = self.error_messages.get_message(last)

            opacity_effect = QGraphicsOpacityEffect(label)
            opacity_effect.setOpacity(0)
            label.setGraphicsEffect(opacity_effect)

            animation = QPropertyAnimation(
                opacity_effect, b"opacity", self.error_messages.container
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


class AutomataTabWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.view = AutomataGraphView(self)
        self.view.setMinimumSize(self.width() // 4, self.height() // 3)

        self.automata_data = AutomataDataWidget(self)
        self.automata_data.setMaximumHeight(2 * self.height() // 3)
        self.automata_data.setMaximumWidth(self.width() // 4)
        self.automata_data.setMinimumWidth(0)

        self.side_panel = SidePanel(self)
        # self.side_panel.sizeHint = lambda: QSize(0, self.height() // 3)
        # self.side_panel.setHidden(True)
        self.errors_panel_width = self.width() // 3
        self.plot_panel_width = self.width() // 3
        side_panel_max_width = max(self.plot_panel_width, self.errors_panel_width)
        self.side_panel.setMaximumWidth(side_panel_max_width)
        self.side_panel.setMinimumWidth(0)

        general_layout = QHBoxLayout(self)
        general_layout.setContentsMargins(0, 0, 0, 0)
        general_layout.addWidget(self.view)
        general_layout.addWidget(self.automata_data, 0, Qt.AlignmentFlag.AlignTop)
        general_layout.addWidget(self.side_panel)

        self.automata_data.verify_button.clicked.connect(self.verify_button_click)
        self.automata_data.draw_button.clicked.connect(self.draw_button_click)
        self.side_panel.close_button.clicked.connect(self.close_panel_button_click)

        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)

    @property
    def is_panel_hidden(self) -> bool:
        return self.side_panel.width() == 0

    def verify_button_click(self) -> None:
        errors = self.check_automata(self.view.to_automata())
        self.show_errors(errors)

    def draw_button_click(self) -> None:
        automata = self.view.to_automata()
        errors = self.check_automata(automata)
        if len(errors) != 0:
            self.show_errors(errors)
            return

        input_alphabet = self.automata_data.input_alphabet()
        output_alphabet = self.automata_data.output_alphabet()

        # Check order of symbols
        # if orders is different then reset it
        if automata.input_alphabet != input_alphabet:
            automata.reset_input_order(input_alphabet)

        if automata.output_alphabet != output_alphabet:
            automata.reset_output_order(output_alphabet)

        prec = 20
        x, y = [], []
        for i in range(prec):
            for word in permutations(automata.input_alphabet, i):
                in_word = "".join(word)
                out_word = automata.read(in_word)
                x.append(automata.to_number(in_word))
                y.append(automata.to_number(out_word))

        if self.side_panel.current_mode != SidePanel.Mode.PLOT:
            self.side_panel.switch_to_plot()

        if not self.is_panel_hidden:
            self.side_panel.draw_plot(x, y)
            return

        def after_finish():
            return self.side_panel.draw_plot(x, y)

        self.show_panel(self.plot_panel_width, after_finish)

    def close_panel_button_click(self) -> None:
        if self.is_panel_hidden:
            return

        def after_finish():
            self.side_panel.switch_to_empty()
            self.side_panel.setSizePolicy(
                QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding
            )
            self.side_panel.setMinimumWidth(0)

        self.hide_panel(after_finish=after_finish)

    def check_automata(self, automata: Automata) -> None:
        input_alphabet = self.automata_data.input_alphabet()
        output_alphabet = self.automata_data.output_alphabet()
        initial_state = self.automata_data.initial_state()

        input_alphabet_check = (
            set(automata.input_alphabet) == set(input_alphabet)
            or len(input_alphabet) == 0
        )
        output_alphabet_check = (
            set(automata.output_alphabet) == set(output_alphabet)
            or len(output_alphabet) == 0
        )
        initial_state_check = (
            automata.initial_state == initial_state or initial_state == ""
        )

        if not (input_alphabet_check and output_alphabet_check and initial_state_check):
            errors = []
            if input_alphabet_check:
                errors.append(
                    "Entered input alphabet doesn't match automata's input alphabet"
                )
            if output_alphabet_check:
                errors.append(
                    "Entered output alphabet doesn't match automata's output alphabet"
                )
            if initial_state_check:
                errors.append(
                    "Errors initial state doesn't macth automata's initial state"
                )
            return errors

        errors = automata.detailed_verificatin()
        if len(errors) != 0:
            return errors

    def show_errors(self, errors: list[str]) -> None:
        is_messages_mode = self.side_panel.current_mode == SidePanel.Mode.ERROR_MESSAGES
        if is_messages_mode and not self.is_panel_hidden:
            self.side_panel.clear_messages()
            self.side_panel.add_messages(*errors)
        else:
            # geom = self.side_panel.geometry()
            # geom.setLeft(geom.right())
            # self.side_panel.setGeometry(geom)
            def after_finish():
                self.side_panel.setSizePolicy(
                    QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
                )
                self.side_panel.add_messages(*errors)

            self.side_panel.switch_to_messages()
            self.show_panel(self.errors_panel_width, after_finish)

    def hide_panel(
        self, dest_width: int = 0, after_finish: Callable[[], None] | None = None
    ) -> None:
        self.toggle_panel(False, dest_width, after_finish)

    def show_panel(
        self, dest_width: int, after_finish: Callable[[], None] | None = None
    ) -> None:
        self.toggle_panel(True, dest_width, after_finish)

    def toggle_panel(
        self,
        flag: bool,
        dest_width: int,
        after_finish: Callable[[], None] | None = None,
    ) -> None:
        group = QSequentialAnimationGroup(self.parentWidget())
        duration = 200

        view_geom = self.view.geometry()
        data_geom = self.automata_data.geometry()
        panel_geom = self.side_panel.geometry()

        dest_view_geom = QRect(self.view.geometry())
        dest_data_geom = QRect(self.automata_data.geometry())
        dest_panel_geom = QRect(self.side_panel.geometry())

        dest_panel_geom.setWidth(dest_width)
        if flag:
            dest_panel_geom.setLeft(panel_geom.right() - dest_width)
            dest_panel_geom.setRight(panel_geom.right())

            dest_data_geom.setWidth(data_geom.width() - dest_width)
            dest_data_geom.setLeft(data_geom.left() - dest_width)
            dest_data_geom.setRight(data_geom.right() - dest_width)

            dest_view_geom.setWidth(view_geom.width() - dest_width)
            dest_view_geom.setRight(view_geom.right() - dest_width)
        else:
            dest_panel_geom.setLeft(panel_geom.right())
            dest_panel_geom.setRight(panel_geom.right())

            dest_data_geom.setWidth(data_geom.width() + panel_geom.width())
            dest_data_geom.setLeft(data_geom.left() + panel_geom.width())
            dest_data_geom.setRight(data_geom.right() + panel_geom.width())

            dest_view_geom.setWidth(view_geom.width() + panel_geom.width())
            dest_view_geom.setRight(view_geom.right() + panel_geom.width())

        view_anim = QPropertyAnimation(self.view, b"geometry", self)
        view_anim.setDuration(duration // 8)
        view_anim.setStartValue(self.view.geometry())
        view_anim.setEndValue(dest_view_geom)
        view_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        data_anim = QPropertyAnimation(self.automata_data, b"geometry")
        data_anim.setDuration(duration // 8)
        data_anim.setStartValue(data_geom)
        data_anim.setEndValue(dest_data_geom)
        data_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        panel_anim = QPropertyAnimation(self.side_panel, b"geometry")
        panel_anim.setDuration(duration * 2)
        panel_anim.setStartValue(panel_geom)
        panel_anim.setEndValue(dest_panel_geom)
        panel_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        if flag:
            group.addAnimation(view_anim)
            group.addPause(20)
            group.addAnimation(data_anim)
            group.addPause(20)
            group.addAnimation(panel_anim)
        else:
            group.addAnimation(panel_anim)
            group.addPause(20)
            group.addAnimation(data_anim)
            group.addPause(20)
            group.addAnimation(view_anim)

        if after_finish:
            panel_anim
            group.finished.connect(after_finish)

        group.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
