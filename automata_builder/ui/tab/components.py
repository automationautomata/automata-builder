import enum
from dataclasses import dataclass
from typing import Callable, Optional

import PyQt6.QtCore as qtc
import PyQt6.QtWidgets as qtw
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PyQt6.QtGui import QAction, QColor, QKeyEvent, QResizeEvent

from automata_builder.core import compute, parser
from automata_builder.core.automata import Automata
from automata_builder.ui.common import (
    FilteredLineEdit,
    FilteredTextEdit,
    OverlayWidget,
    VerticalMessagesWidget,
)
from automata_builder.ui.graphics.view import BuilderView
from automata_builder.ui.tab.components import *


class AlphabetEdit(qtw.QTextEdit):
    def __init__(self, text: str = "", parent: Optional[qtw.QWidget] = None) -> None:
        super().__init__(text, parent)
        self.textChanged.connect(self.format_text)
        self.setPlaceholderText("{0, 1, 2, 3}")
        self.prev_text = self.toPlainText()

    def format_text(self) -> None:
        text = self.toPlainText()

        cursor = self.textCursor()
        pos = cursor.position()
        cur = text[pos - 1] if pos != 0 else ""
        new_pos = pos

        is_adding = len(text) > len(self.prev_text)

        if cur in {"\n", "\t", "\r", "{", "}"} and is_adding:
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
                # pos + 1

            inner_text = text[2:-2]
            symbols = [s.strip() for s in inner_text.split(",") if s]

            if not is_adding:
                symbols = [s for s in symbols if s.strip()]

            unique = dict.fromkeys(symbols)
            text = "{ " + ", ".join(unique) + " }"
            new_pos = pos + 1 if is_insert and is_adding else pos

        self.blockSignals(True)
        self.setText(text)
        self.blockSignals(False)

        cursor.setPosition(new_pos, cursor.MoveMode.MoveAnchor)
        self.setTextCursor(cursor)

        self.prev_text = text

    def alphabet(self) -> list[str]:
        text = self.toPlainText()
        alphabet = text[2:-2].split(", ")
        return alphabet if alphabet[0] else []

    def set_alphabet(self, alphabet: list[str]) -> None:
        text = "{" + ", ".join(alphabet) + "}"
        self.blockSignals(True)
        self.setText(text)
        self.blockSignals(False)


class Parameters(qtw.QWidget):
    def __init__(
        self,
        word_input_condition: Callable[[], None],
        parent: Optional[qtw.QWidget] = None,
        alphabet_item_height: int = 50,
        spacing_height: int = 10,
    ) -> None:
        super().__init__(parent)
        self.input_alphabet_field = AlphabetEdit(parent=self)
        self.input_alphabet_field.setMinimumHeight(alphabet_item_height)

        self.output_alphabet_field = AlphabetEdit(parent=self)
        self.output_alphabet_field.setMinimumHeight(alphabet_item_height)

        self.initial_state_field = FilteredLineEdit(self.state_input_condition)
        self.initial_state_field.setPlaceholderText("initial state")

        self.verify_button = qtw.QPushButton("Verify")

        self.last_state_field = FilteredLineEdit(self.state_input_condition)
        self.last_state_field.setPlaceholderText("last state")

        self.prefix_field = FilteredLineEdit(word_input_condition)
        self.prefix_field.setPlaceholderText("prefix")

        self.suffix_field = FilteredLineEdit(word_input_condition)
        self.suffix_field.setPlaceholderText("suffix")

        self.draw_button = qtw.QPushButton("Draw")
        self.draw_curves_button = qtw.QPushButton("Draw curves")
        self.draw_curves_button.setVisible(False)
        layout = qtw.QVBoxLayout()
        layout.setAlignment(qtc.Qt.AlignmentFlag.AlignTop)

        layout.addWidget(qtw.QLabel("Input alphabet"))
        layout.addWidget(self.input_alphabet_field)

        layout.addSpacing(alphabet_item_height // 5)
        layout.addWidget(qtw.QLabel("Output alphabet"))
        layout.addWidget(self.output_alphabet_field)

        layout.addSpacing(alphabet_item_height // 5)
        layout.addWidget(qtw.QLabel("Initial state"))
        layout.addWidget(self.initial_state_field)

        layout.addSpacing(alphabet_item_height // 5)
        layout.addWidget(self.verify_button)

        filters_layout = qtw.QVBoxLayout()
        filters_layout.setSpacing(spacing_height)

        filters_layout.addWidget(self.last_state_field)
        filters_layout.addWidget(self.prefix_field)
        filters_layout.addWidget(self.suffix_field)
        filters_layout.addWidget(self.draw_button)

        layout.addLayout(filters_layout)
        layout.addWidget(self.draw_curves_button)

        self.setLayout(layout)

    def state_input_condition(self, text) -> None:
        filtered_text = "".join(s for s in text if s not in "\r\t\n ")
        return filtered_text == text

    def input_alphabet(self) -> list[str]:
        return self.input_alphabet_field.alphabet()

    def output_alphabet(self) -> list[str]:
        return self.output_alphabet_field.alphabet()

    def initial_state(self) -> str:
        return self.initial_state_field.text()

    def prefix(self) -> str:
        return self.prefix_field.text()

    def suffix(self) -> str:
        return self.suffix_field.text()

    def last_state(self) -> str:
        return self.last_state_field.text()

    def load_draw_filters(self, prefix: str, suffix: str, last_state: str) -> None:
        self.prefix_field.set_text(prefix)
        self.suffix_field.set_text(suffix)
        self.last_state_field.setText(last_state)

    def load_data(
        self, input_alphabet: list[str], output_alphabet: list[str], initial_state: str
    ) -> None:
        self.input_alphabet_field.set_alphabet(input_alphabet)
        self.output_alphabet_field.set_alphabet(output_alphabet)
        self.initial_state_field.setText(initial_state)

    def is_empty(self):
        return self.input_alphabet() or self.output_alphabet() or self.initial_state()


@dataclass
class Points:
    x: list[int]
    y: list[int]
    xlim: Optional[tuple[int, int]]
    ylim: Optional[tuple[int, int]]
    is_plot: bool = False
    color: str = "red"


class PlotWidget(qtw.QWidget):
    def __init__(self, parent: Optional[qtw.QWidget] = None):
        super().__init__(parent)
        fig = Figure(figsize=(5, 5))
        self.canvas = FigureCanvasQTAgg(fig)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        self.ax = self.canvas.figure.add_subplot(111)

        layout = qtw.QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def draw(self, *points: Points, title: str = "") -> None:
        shift = 0.2
        self.ax.clear()
        compute.draw(self.ax, *points, border_shift=shift, title=title, grid=True)

        self.canvas.draw()


class SidePanel(qtw.QWidget):
    class Mode(enum.Enum):
        ERROR_MESSAGES = enum.auto()
        PLOT = enum.auto()
        EMPTY = enum.auto()

    def __init__(self, parent: Optional[qtw.QWidget] = None) -> None:
        super().__init__(parent)
        self.cur_mode_ = self.Mode.EMPTY

        self.container = qtw.QWidget(self)
        self.container.setSizePolicy(
            qtw.QSizePolicy.Policy.Expanding, qtw.QSizePolicy.Policy.Expanding
        )

        self.error_messages = VerticalMessagesWidget()
        self.error_messages.setContentsMargins(0, 0, 0, 0)
        self.error_messages.setSizePolicy(
            qtw.QSizePolicy.Policy.Expanding, qtw.QSizePolicy.Policy.Expanding
        )

        self.plot = PlotWidget()
        self.plot.setContentsMargins(0, 0, 0, 0)
        self.plot.setSizePolicy(
            qtw.QSizePolicy.Policy.Expanding, qtw.QSizePolicy.Policy.Expanding
        )

        self.stack_layout = qtw.QStackedLayout()
        self.stack_layout.addWidget(self.error_messages)
        self.stack_layout.addWidget(self.plot)

        self.close_button = qtw.QPushButton(">>")

        self.main_layout = qtw.QVBoxLayout(self.container)
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
            self.cur_mode_ = self.Mode.PLOT

        elif mode == self.Mode.EMPTY:
            self.stack_layout.setCurrentWidget(None)
            self.cur_mode_ = self.Mode.EMPTY

    def add_messages(self, *messages: str) -> None:
        if self.current_mode != self.Mode.ERROR_MESSAGES:
            raise Exception("Error messages widget doesn't set")

        group = qtc.QSequentialAnimationGroup(self.error_messages)

        pause = 120
        for msg in messages:
            self.error_messages.add_message(msg)
            last = self.error_messages.count() - 1
            label = self.error_messages.get_message(last)

            opacity_effect = qtw.QGraphicsOpacityEffect(label)
            opacity_effect.setOpacity(0)
            label.setGraphicsEffect(opacity_effect)

            animation = qtc.QPropertyAnimation(
                opacity_effect, b"opacity", self.error_messages
            )
            animation.setDuration(400)
            animation.setStartValue(0)
            animation.setEndValue(1)
            animation.setEasingCurve(qtc.QEasingCurve.Type.InOutQuad)

            group.addAnimation(animation)
            group.addPause(pause)

        group.start(qtc.QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)

    def clear_messages(self) -> None:
        if self.current_mode != self.Mode.ERROR_MESSAGES:
            raise Exception("Error messages widget doesn't set")
        self.error_messages.clear()

    def draw_plot(self, *points: Points) -> None:
        # xlim = xmin, xmax
        # ylim = ymin, ymax
        if self.current_mode not in (self.Mode.EMPTY, self.Mode.PLOT):
            raise Exception("Plot widget doesn't set")

        if self.current_mode == self.Mode.EMPTY:
            self.set_mode(self.Mode.PLOT)

        self.plot.draw(*points)

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


class WordProcessing(qtw.QWidget):
    def __init__(
        self,
        input_word_condition: Callable[[str], bool],
        output_word_condition: Callable[[str], bool],
        parent: Optional[qtw.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setSizePolicy(
            qtw.QSizePolicy.Policy.Expanding, qtw.QSizePolicy.Policy.Preferred
        )

        self.input_word_edit = FilteredLineEdit(input_word_condition)
        self.input_word_edit.setPlaceholderText("Input word")
        self.input_word_edit.setSizePolicy(
            qtw.QSizePolicy.Policy.Expanding, qtw.QSizePolicy.Policy.Preferred
        )

        self.output_word_edit = FilteredLineEdit(output_word_condition)
        self.output_word_edit.setPlaceholderText("Output word")
        self.output_word_edit.setSizePolicy(
            qtw.QSizePolicy.Policy.Expanding, qtw.QSizePolicy.Policy.Preferred
        )

        layout = qtw.QVBoxLayout()
        layout.addWidget(self.input_word_edit)
        layout.addWidget(self.output_word_edit)

        self.forward_button = qtw.QPushButton(text=">")
        self.forward_button.setContentsMargins(0, 0, 0, 0)

        self.backword_button = qtw.QPushButton(text="<")
        self.backword_button.setContentsMargins(0, 0, 0, 0)

        buttons_layout = qtw.QHBoxLayout()
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.addWidget(self.backword_button)
        buttons_layout.addWidget(self.forward_button)

        self.clear_button = qtw.QPushButton(text="clear")

        processing_layout = qtw.QVBoxLayout()
        processing_layout.setContentsMargins(0, 0, 0, 0)
        processing_layout.addLayout(buttons_layout)
        processing_layout.addWidget(self.clear_button)

        main_layout = qtw.QHBoxLayout()
        main_layout.addLayout(layout)
        main_layout.addLayout(processing_layout)
        main_layout.setAlignment(buttons_layout, qtc.Qt.AlignmentFlag.AlignTop)

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


class TactCounter(OverlayWidget):
    def __init__(self, parent: Optional[qtw.QWidget] = None):
        super().__init__(parent)
        self.value_ = 0
        self.counter = qtw.QLabel("0", self)
        self.counter.setSizePolicy(
            qtw.QSizePolicy.Policy.Expanding, qtw.QSizePolicy.Policy.Expanding
        )

        self.setContextMenuPolicy(qtc.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.custom_menu)

    def custom_menu(self, point: qtc.QPoint):
        menu = qtw.QMenu(self)

        hide_action = QAction("Скрыть")
        hide_action.triggered.connect(lambda: self.setHidden(True))

        menu.addAction(hide_action)
        menu.exec(self.mapToGlobal(point))

    @property
    def value(self):
        return self.value_

    @value.setter
    def value(self, new_value: int):
        self.value_ = new_value
        self.counter.setText(str(self.value))
        self.counter.adjustSize()

    def increnemt(self):
        self.value_ += 1
        self.counter.setText(str(self.value))
        self.counter.adjustSize()

    def decrement(self):
        self.value_ -= 1
        self.counter.setText(str(self.value))
        self.counter.adjustSize()


class AutomataContainer(qtw.QWidget):
    MARKED_COLOR = QColor(128, 0, 0)

    def __init__(
        self,
        parent: Optional[qtw.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.view = BuilderView()
        self.view.fitInView(
            qtc.QRectF(0, 0, self.height() * 0.9, self.width() * 0.9),
            qtc.Qt.AspectRatioMode.KeepAspectRatio,
        )
        self.view.setSizePolicy(
            qtw.QSizePolicy.Policy.Expanding, qtw.QSizePolicy.Policy.Expanding
        )

        self.word_processing = WordProcessing(self.filter_input, lambda _: True)
        self.word_processing.setMinimumHeight(self.height() // 6)
        self.word_processing.setMaximumWidth(self.width())
        self.word_processing.setSizePolicy(
            qtw.QSizePolicy.Policy.Expanding, qtw.QSizePolicy.Policy.Expanding
        )
        self.word_processing.forward_button.clicked.connect(self.forward_click)
        self.word_processing.backword_button.clicked.connect(self.backward_click)
        self.word_processing.clear_button.clicked.connect(self.clear_click)

        layout = qtw.QVBoxLayout()
        layout.addWidget(self.view)
        layout.addWidget(self.word_processing, 0, qtc.Qt.AlignmentFlag.AlignTop)
        self.setLayout(layout)

        # --------------------------------------
        self.tact_counter = TactCounter(self)  # tact counter overlay view
        self.tact_counter.setHidden(True)
        # --------------------------------------

        self.prev_input_word = self.word_processing.input_word
        self.transitions_history = []
        self.automata_errors_handler = None

    def resizeEvent(self, event: QResizeEvent | None = None):
        self.draw_tact_counter()
        return super().resizeEvent(event)

    def keyPressEvent(self, event: QKeyEvent | None) -> None:
        key = event.key()
        modifier = event.modifiers()

        if (
            key == qtc.Qt.Key.Key_S
            and modifier == qtc.Qt.KeyboardModifier.ControlModifier
        ):
            self.view.save_view()

        return super().keyPressEvent(event)

    def draw_tact_counter(self):
        shift = 10
        pos = self.view.geometry().bottomLeft()
        pos.setX(pos.x() + shift)
        pos.setY(pos.y() - shift)

        new_geom = self.tact_counter.geometry()
        new_geom.moveBottomLeft(pos)
        self.tact_counter.setGeometry(new_geom)

    def set_automata_errors_handler(
        self, automata_errors_handler: Callable[[Automata], bool]
    ) -> None:
        self.automata_errors_handler = automata_errors_handler

    def automata(self) -> tuple[Automata | None, list[str]]:
        return Automata.detailed_build(*self.automata_tables())

    def automata_tables(self) -> tuple[str, dict[str, list], dict[str, list]]:
        initial_state = self.view.initial_state()
        transitions_table = self.view.get_transitions_table()
        outputs_table = self.view.get_outputs_table()
        return initial_state, transitions_table, outputs_table

    def filter_input(self, word: str) -> None:
        automata, errors = self.automata()
        if not automata:
            if self.automata_errors_handler:
                self.automata_errors_handler(errors)
            return False

        input_alphabet = automata.inputs
        if set(input_alphabet).issuperset(word):
            return True

        qtw.QMessageBox.warning(self, "Error", "Invalid input symbol")
        return False

    def forward_click(self) -> None:
        if not (self.word_processing.input_word and self.automata_errors_handler):
            return

        automata, errors = self.automata()
        if not automata:
            self.automata_errors_handler(errors)
            return

        input_word = self.word_processing.input_word
        output_word = self.word_processing.output_word
        # > - in case the input_word last symbols was removed
        if len(output_word) >= len(input_word):
            return

        n = len(output_word)
        if n == 0:
            self.transitions_history.clear()
            cur_state = automata.initial_state
        else:
            cur_state = self.transitions_history[-1]

        cur_symb = input_word[n]
        new_state, out_ = automata.transition(cur_symb, cur_state)

        self.view.unmark_node(cur_state)
        self.view.mark_node(new_state, self.MARKED_COLOR)

        self.word_processing.append_to_output(out_)
        self.transitions_history.append(new_state)

        if self.tact_counter.isHidden():
            # if tact_counter was closed, while word was processing
            self.tact_counter.setVisible(True)
            self.tact_counter.value = n + 1
        else:
            self.tact_counter.increnemt()

    def backward_click(self) -> None:
        if not (self.word_processing.input_word and self.automata_errors_handler):
            return

        if len(self.transitions_history) == 0:
            return

        # Reduce on 1 symbol output word
        output_word = self.word_processing.output_word
        self.word_processing.output_word = output_word[:-1]

        # Mark previous state
        state = self.transitions_history.pop()
        self.view.unmark_node(state)
        if len(self.transitions_history) != 0:
            prev_state = self.transitions_history[-1]
            self.view.mark_node(prev_state, self.MARKED_COLOR)

        if self.tact_counter.isHidden():
            # if tact_counter was closed, while word was processing
            self.tact_counter.setVisible(True)
            self.tact_counter.value = len(self.word_processing.output_word)
        else:
            self.tact_counter.decrement()

    def clear_click(self):
        self.word_processing.input_word = ""
        self.word_processing.output_word = ""
        if len(self.transitions_history) != 0:
            state = self.transitions_history[-1]
            self.view.unmark_node(state)
        self.transitions_history.clear()
        self.tact_counter.setHidden(True)

    def is_empty_scene(self):
        return self.view.is_empty()


class FunctionInput(qtw.QWidget):
    VARIABLE_NAME = "x"

    def __init__(self, parent: Optional[qtw.QWidget] = None) -> None:
        super().__init__(parent)

        self.func_input = FilteredTextEdit(self._filter_condition_)
        self.func_input.setPlaceholderText("function")

        self.base_input = FilteredLineEdit(lambda text: text.isnumeric() or not text)
        self.base_input.setPlaceholderText("base")
        self.base_input.set_text("")

        self.draw_button = qtw.QPushButton("Draw from function")

        self._layout = qtw.QVBoxLayout(self)
        self._layout.addWidget(self.func_input)
        self._layout.addWidget(self.base_input)
        self._layout.addWidget(self.draw_button)

    @staticmethod
    def _filter_condition_(text: str) -> bool:
        allowed = set([" ", "(", ")", FunctionInput.VARIABLE_NAME])
        allowed.update(f"{i}" for i in range(10))
        allowed.update(parser.allowed_operations())
        return allowed.issuperset(set(text))

    def get_function(self, base: int) -> Callable[[int], int]:
        expr = self.func_input.toPlainText()
        valid_expr = parser.parse_expression(expr, base)
        return eval(f"lambda x: {valid_expr}")

    def get_function_text(self) -> Callable[[int], int]:
        return self.func_input.toPlainText()

    def get_base(self) -> int:
        text = self.base_input.text()
        return int(text) if len(text) != 0 else 0

    def load(self, func: str, base: int) -> None:
        self.func_input.set_text(func)
        self.base_input.set_text(str(base))


class LengthInput(qtw.QWidget):
    def __init__(
        self, parent: Optional[qtw.QWidget] = None, default_len: int = 12
    ) -> None:
        super().__init__(parent)
        self.default_len = default_len

        self.label = qtw.QLabel(text="Length")
        self.input_field = FilteredLineEdit(lambda text: text.isnumeric() or not text)
        self.input_field.setPlaceholderText(f"length (default is {self.default_len})")

        self._layout = qtw.QVBoxLayout(self)
        self._layout.addWidget(self.label)
        self._layout.addWidget(self.input_field)

    def get_length(self) -> int:
        text = self.input_field.text()
        return int(text) if len(text) != 0 else self.default_len

    def load(self, length: int) -> None:
        self.input_field.set_text(str(length))
