import enum
from typing import Any, Callable

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

from graphics import AutomataGraphView
from tools.widgets import VerticalMessagesWidget


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

        is_symbol_added = len(text) > len(self.prev_text)

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
            if cur == " " and text[pos - 2] not in ", " and is_symbol_added:
                text = f"{text[: pos - 1]}, {text[pos:]}"
            elif cur == "," and is_symbol_added:
                text = f"{text[:pos]} {text[pos:]}"

            text = text[2:-2]

            if is_symbol_added:
                symbols = [s.strip() for s in text.split(",") if s]
                new_pos = pos + 1 if pos != len(text) - 2 else pos
            else:
                symbols = [s.strip() for s in text.split(",") if s.strip()]

            text = "{ " + ", ".join(dict.fromkeys(symbols)) + " }"

        self.blockSignals(True)
        self.setText(text)
        self.blockSignals(False)

        cursor.setPosition(new_pos, cursor.MoveMode.MoveAnchor)
        self.setTextCursor(cursor)

        self.prev_text = text


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
        self.output_alphabet_field = AlphabetEdit(parent=self)
        self.initial_state_field = QTextEdit(self)

        self.verify_button = QPushButton("Verify", self)

        self.input_alphabet_field.setMaximumHeight(alphabet_item_height)
        self.output_alphabet_field.setMaximumHeight(alphabet_item_height)

        self.initial_state_field.setPlaceholderText("initial state")

        text_layout = QVBoxLayout(self)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        text_layout.setSpacing(4)
        text_layout.addWidget(self.input_alphabet_title)
        text_layout.addWidget(self.input_alphabet_field)

        text_layout.addSpacing(alphabet_item_height // 3)
        text_layout.addWidget(self.output_alphabet_title)
        text_layout.addWidget(self.output_alphabet_field)

        text_layout.addSpacing(alphabet_item_height // 3)
        text_layout.addWidget(self.initial_state_title)
        text_layout.addWidget(self.initial_state_field)

        text_layout.addSpacing(initial_state_height // 3)
        text_layout.addWidget(self.verify_button)

    def input_alphabet(self) -> list[str]:
        return self.input_alphabet_field.toPlainText()[2:-2].split(", ")

    def output_alphabet(self) -> list[str]:
        return self.output_alphabet_field.toPlainText()[2:-2].split(", ")


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
        self.plot: None = None

        self.button = QPushButton(">>")

        self.stack_layout = QStackedLayout()
        self.stack_layout.addWidget(self.error_messages)

        self.main_layout = QVBoxLayout(self.container)

        self.main_layout.addLayout(self.stack_layout)
        self.main_layout.addWidget(self.button)
        self.main_layout.addWidget(None)

    def resizeEvent(self, a0) -> None:
        self.blockSignals(True)
        self.container.resize(self.size())
        self.blockSignals(False)
        return super().resizeEvent(a0)

    @property
    def current_mode(self):
        return self.cur_mode_

    def set_mode(self, mode: Mode):
        # fields = self.__dict__.keys() - self.__class__.__dict__.keys()

        if mode == self.Mode.ERROR_MESSAGES:
            self.stack_layout.setCurrentWidget(self.error_messages)
            # for field_name in fields:
            #     value = getattr(self, field_name)
            #     if isinstance(value, QWidget) and not isinstance(
            #         value, (VerticalMessagesWidget, QPushButton)
            #     ):
            #         setattr(self, field_name, None)
            #         value.deleteLater()
            self.cur_mode_ = self.Mode.ERROR_MESSAGES
            return

        if mode == self.Mode.PLOT:
            self.stack_layout.setCurrentWidget(self.plot)
            # for field_name in fields:
            #     value = getattr(self, field_name)
            #     if isinstance(value, QWidget) and not isinstance(
            #         value, (VerticalMessagesWidget, QPushButton)
            #     ):
            #         setattr(self, field_name, None)
            #         value.deleteLater()
            self.cur_mode_ = self.Mode.ERROR_MESSAGES
            return

        if mode == self.Mode.EMPTY:
            self.stack_layout.setCurrentWidget(None)
            self.cur_mode_ = self.Mode.EMPTY
            return

    def add_messages(self, *messages: tuple[str]):
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

    def clear_messages(self):
        if self.current_mode != self.Mode.ERROR_MESSAGES:
            raise Exception("Error messages widget doesn't set")
        self.error_messages.clear()

    def switch_to_messages_widget(self):
        if self.current_mode == self.Mode.ERROR_MESSAGES:
            raise Exception("Error messages widget is already set")

        self.set_mode(self.Mode.ERROR_MESSAGES)

        # self.error_messages.setMaximumSize(self.size())

    def switch_to_plot(self):
        if self.current_mode == self.Mode.PLOT:
            raise Exception("Plot widget is already set")
        self.set_mode(self.Mode.PLOT)

    def switch_to_empty(self):
        self.set_mode(self.Mode.EMPTY)


class AutomataTabWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.view = AutomataGraphView(self)
        self.view.setContentsMargins(4, 4, 4, 4)
        self.view.setMinimumSize(self.width() // 4, self.height() // 3)

        self.automata_data = AutomataDataWidget(self)
        self.automata_data.setMaximumHeight(2 * self.height() // 3)
        self.automata_data.setMaximumWidth(self.width() // 4)
        self.automata_data.setMinimumWidth(0)

        self.hidden_panel = SidePanel(self)
        # self.hidden_panel.sizeHint = lambda: QSize(0, self.height() // 3)
        # self.hidden_panel.setHidden(True)
        self.errors_panel_width = self.width() // 3
        self.plot_panel_width = self.width() // 3
        hidden_panel_max_width = max(self.plot_panel_width, self.errors_panel_width)
        self.hidden_panel.setMaximumWidth(hidden_panel_max_width)
        self.hidden_panel.setMinimumWidth(0)

        general_layout = QHBoxLayout(self)
        general_layout.setContentsMargins(0, 0, 0, 0)
        general_layout.addWidget(self.view)
        general_layout.addWidget(self.automata_data, Qt.AlignmentFlag.AlignTop)
        general_layout.addWidget(self.hidden_panel)

        self.automata_data.verify_button.clicked.connect(self.verify_button_click)
        self.hidden_panel.button.clicked.connect(self.close_panel_button_click)

        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)

    def verify_button_click(self) -> None:
        errors = ["Holds multiple widgets but displays only one at a time.", "2, 3"]

        if self.hidden_panel.current_mode == SidePanel.Mode.ERROR_MESSAGES:
            self.hidden_panel.clear_messages()
            self.hidden_panel.add_messages(*errors)
        else:
            # geom = self.hidden_panel.geometry()
            # geom.setLeft(geom.right())
            # self.hidden_panel.setGeometry(geom)
            self.hidden_panel.switch_to_messages_widget()

            def after_finish():
                self.hidden_panel.setSizePolicy(
                    QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
                )
                self.hidden_panel.add_messages(*errors)

            self.show_panel(self.errors_panel_width, after_finish)

    def close_panel_button_click(self) -> None:
        if self.panel_state:
            return

        def after_finish():
            self.hidden_panel.switch_to_empty()
            self.hidden_panel.setSizePolicy(
                QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding
            )
            self.hidden_panel.setMinimumWidth(0)

        self.hide_panel(after_finish=after_finish)

    @property
    def panel_state(self) -> bool:
        return self.hidden_panel.width() == 0

    def hide_panel(
        self, dest_width: int = 0, after_finish: Callable[[Any], None] | None = None
    ) -> None:
        self.toggle_panel(False, dest_width, after_finish)

    def show_panel(
        self, dest_width: int, after_finish: Callable[[Any], None] | None = None
    ) -> None:
        self.toggle_panel(True, dest_width, after_finish)

    def toggle_panel(
        self,
        flag: bool,
        dest_width: int,
        after_finish: Callable[[Any], None] | None = None,
    ) -> None:
        group = QSequentialAnimationGroup(self.parentWidget())
        duration = 200

        view_geom = self.view.geometry()
        data_geom = self.automata_data.geometry()
        panel_geom = self.hidden_panel.geometry()

        dest_view_geom = QRect(self.view.geometry())
        dest_data_geom = QRect(self.automata_data.geometry())
        dest_panel_geom = QRect(self.hidden_panel.geometry())

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
        view_anim.setDuration(20)
        view_anim.setStartValue(self.view.geometry())
        view_anim.setEndValue(dest_view_geom)
        view_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        data_anim = QPropertyAnimation(self.automata_data, b"geometry")
        data_anim.setDuration(20)
        data_anim.setStartValue(data_geom)
        data_anim.setEndValue(dest_data_geom)
        data_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        panel_anim = QPropertyAnimation(self.hidden_panel, b"geometry")
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
