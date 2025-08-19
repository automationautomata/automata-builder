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
    QHBoxLayout,
    QMessageBox,
    QSizePolicy,
    QWidget,
)

from ..automata import Automata
from ..tab.components import *


class AutomataTab(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.automata_container = AutomataContainer()
        self.automata_container.setMinimumWidth(self.width() // 4)
        self.automata_container.setMinimumHeight(self.height() // 3)
        self.automata_container.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        self.params_panel = ParametersPanel(self.word_input_condition)
        self.params_panel.setMaximumHeight(int(0.94 * self.height()))
        self.params_panel.setMaximumWidth(self.width() // 4)
        self.params_panel.setMinimumWidth(0)

        self.errors_panel_width = self.width() // 3
        self.plot_panel_width = self.height()
        side_panel_max_width = max(self.plot_panel_width, self.errors_panel_width)

        self.side_panel = SidePanel()
        self.side_panel.setMaximumWidth(side_panel_max_width)
        self.side_panel.setMinimumWidth(0)

        self.layout_ = QHBoxLayout(self)
        self.layout_.setContentsMargins(0, 0, 0, 0)
        self.layout_.addWidget(self.automata_container, 2)
        self.layout_.addWidget(self.params_panel, 0, Qt.AlignmentFlag.AlignTop)
        self.layout_.addWidget(self.side_panel, 0)

        self.params_panel.verify_button.clicked.connect(self.verify_click)
        self.params_panel.draw_button.clicked.connect(self.draw_click)
        self.side_panel.close_button.clicked.connect(self.close_panel_click)

        self.automata_container.set_automata_errors_handler(self.show_errors)

        self.prev_prefix_text = self.params_panel.prefix_field.toPlainText()
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)

    def automata(self) -> Automata | None:
        """Return automata or show errors and return None if automata is incorrect"""
        automata, errors = self.automata_container.automata()
        if automata:
            errors = self.compare_data(
                automata.input_alphabet,
                automata.output_alphabet,
                automata.initial_state,
            )
        if len(errors) != 0:
            self.show_errors(errors)
            return None
        return automata

    def is_panel_hidden(self) -> bool:
        return self.side_panel.width() == 0

    def verify_click(self) -> None:
        automata = self.automata()
        if not automata:
            return

        self.params_panel.set_data(
            automata.input_alphabet,
            automata.output_alphabet,
            automata.initial_state,
        )
        QMessageBox.information(self, "Notification", "Automata is correct")
        # self.toggle_panel()

    def draw_click(self) -> None:
        automata = self.automata()
        if not automata:
            return

        input_alphabet = self.params_panel.input_alphabet()
        output_alphabet = self.params_panel.output_alphabet()

        # Check order of symbols
        # if orders is different then reset it
        if automata.input_alphabet != input_alphabet and len(input_alphabet) != 0:
            automata.reset_inputs_order(input_alphabet)

        if automata.output_alphabet != output_alphabet and len(input_alphabet) != 0:
            automata.reset_outputs_order(output_alphabet)

        self.params_panel.set_data(
            automata.input_alphabet,
            automata.output_alphabet,
            automata.initial_state,
        )

        prefix = self.params_panel.prefix()
        suffix = self.params_panel.suffix()
        last_state = self.params_panel.last_state()
        if last_state and last_state not in automata.states:
            self.show_errors(["Incorrect last state"])
            return

        prec = 14
        x, y = [], []
        for i in range(1, prec):
            pairs = automata.pairs_generator(i, prefix, suffix, last_state)
            for in_word, out_word in pairs:
                x.append(automata.to_number(in_word))
                y.append(automata.to_number(out_word))

        if self.side_panel.current_mode != SidePanel.Mode.PLOT:
            self.side_panel.switch_to_plot()

        if not self.is_panel_hidden():
            xlim = 1, len(automata.input_alphabet) + 1
            ylim = 1, len(automata.output_alphabet) + 1
            self.side_panel.draw_plot(x, y, xlim, ylim)
            return

        def after_finish():
            xlim = 1, len(automata.input_alphabet) + 1
            ylim = 1, len(automata.output_alphabet) + 1
            self.side_panel.draw_plot(x, y, xlim, ylim)

        self.toggle_panel(self.plot_panel_width, after_finish)

    def close_panel_click(self) -> None:
        if self.is_panel_hidden():
            return

        def after_finish():
            self.side_panel.switch_to_empty()
            self.side_panel.setSizePolicy(
                QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding
            )
            self.side_panel.setMinimumWidth(0)

        self.toggle_panel(after_finish=after_finish)

    def word_input_condition(self, text: str) -> bool:
        automata, _ = self.automata_container.automata()
        if not automata:
            return False
        symbols = set(text)
        errors = self.compare_data(
            automata.input_alphabet,
            automata.output_alphabet,
            automata.initial_state,
        )
        return len(errors) == 0 and symbols.issubset(automata.input_alphabet)

    def compare_data(
        self, input_alphabet: list[str], output_alphabet: list[str], initial_state: str
    ) -> list[str]:
        entered_input_alphabet = self.params_panel.input_alphabet()
        entered_output_alphabet = self.params_panel.output_alphabet()
        entered_initial_state = self.params_panel.initial_state()

        input_alphabet_check = (
            set(input_alphabet) == set(entered_input_alphabet)
            or len(entered_input_alphabet) == 0
        )
        output_alphabet_check = (
            set(entered_output_alphabet).issuperset(output_alphabet)
            or len(entered_output_alphabet) == 0
        )
        initial_state_check = (
            initial_state == entered_initial_state or not entered_initial_state
        )

        if input_alphabet_check and output_alphabet_check and initial_state_check:
            return []

        errors = []
        if not input_alphabet_check:
            errors.append(
                "Entered input alphabet doesn't match automata's input alphabet"
            )
        if not output_alphabet_check:
            errors.append(
                "Entered output alphabet doesn't match automata's output alphabet"
            )
        if not initial_state_check:
            errors.append("Initial state doesn't macth automata's initial state")
        return errors

    def show_errors(self, errors: list[str]) -> None:
        if self.side_panel.current_mode == SidePanel.Mode.ERROR_MESSAGES:
            self.side_panel.clear_messages()
            self.side_panel.add_messages(*errors)
            return

        self.side_panel.switch_to_messages()
        self.side_panel.clear_messages()

        def after_finish():
            self.side_panel.add_messages(*errors)

        self.toggle_panel(self.errors_panel_width, after_finish)

    def toggle_panel(
        self, dest_width: int = 0, after_finish: Callable[[], None] | None = None
    ) -> None:
        group = QSequentialAnimationGroup(self.parentWidget())
        duration = 200

        auto_geom = self.automata_container.geometry()
        data_geom = self.params_panel.geometry()
        panel_geom = self.side_panel.geometry()

        dest_auto_geom = QRect(self.automata_container.geometry())
        dest_data_geom = QRect(self.params_panel.geometry())
        dest_panel_geom = QRect(self.side_panel.geometry())

        dest_panel_geom.setWidth(dest_width)

        width_diff = dest_width - panel_geom.width()

        dest_panel_geom.setLeft(panel_geom.left() - width_diff)
        dest_panel_geom.setRight(panel_geom.right())

        dest_data_geom.setWidth(data_geom.width() - width_diff)
        dest_data_geom.setLeft(data_geom.left() - width_diff)
        dest_data_geom.setRight(data_geom.right() - width_diff)

        dest_auto_geom.setWidth(auto_geom.width() - width_diff)
        dest_auto_geom.setRight(auto_geom.right() - width_diff)

        auto_anim = QPropertyAnimation(self.automata_container, b"geometry", self)
        auto_anim.setDuration(duration // 8)
        auto_anim.setStartValue(self.automata_container.geometry())
        auto_anim.setEndValue(dest_auto_geom)
        auto_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        data_anim = QPropertyAnimation(self.params_panel, b"geometry")
        data_anim.setDuration(duration // 8)
        data_anim.setStartValue(data_geom)
        data_anim.setEndValue(dest_data_geom)
        data_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        panel_anim = QPropertyAnimation(self.side_panel, b"geometry")
        panel_anim.setDuration(duration * 2)
        panel_anim.setStartValue(panel_geom)
        panel_anim.setEndValue(dest_panel_geom)
        panel_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        if width_diff > 0:
            group.addAnimation(auto_anim)
            group.addPause(20)
            group.addAnimation(data_anim)
            group.addPause(20)
            group.addAnimation(panel_anim)
        else:
            group.addAnimation(panel_anim)
            group.addPause(20)
            group.addAnimation(data_anim)
            group.addPause(20)
            group.addAnimation(auto_anim)

        def on_finish():
            self.side_panel.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            i = self.layout_.indexOf(self.side_panel)
            j = self.layout_.indexOf(self.automata_container)
            if width_diff > 0:
                self.side_panel.setMaximumWidth(dest_width)
                self.layout_.setStretch(i, 2)
                self.layout_.setStretch(j, 1)
            else:
                self.layout_.setStretch(i, 0)
                self.layout_.setStretch(j, 2)

            if after_finish:
                after_finish()

        group.finished.connect(on_finish)

        group.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)

    def load(self, data: dict) -> None:
        params = data["params"]
        self.params_panel.set_data(
            params["input_alphabet"],
            params["output_alphabet"],
            params["initial_state"],
        )
        self.params_panel.set_draw_filters(
            params["prefix"],
            params["suffix"],
            params["last_state"],
        )
        scene = self.automata_container.view.scene()
        scene.deserialize(data["scene"])

    def dump(self) -> dict:
        params = {
            "input_alphabet": self.params_panel.input_alphabet(),
            "output_alphabet": self.params_panel.output_alphabet(),
            "initial_state": self.params_panel.initial_state(),
            "prefix": self.params_panel.prefix(),
            "suffix": self.params_panel.suffix(),
            "last_state": self.params_panel.last_state(),
        }
        scene = self.automata_container.view.scene()
        return {"params": params, "scene": scene.serialize()}

    def is_empty(self):
        return self.automata_container.is_empty_scene() or self.params_panel.is_empty()
