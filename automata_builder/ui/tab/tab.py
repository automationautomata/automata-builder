from threading import Event
from typing import Callable, Optional

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
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from automata_builder.core import compute
from automata_builder.core.automata import Automata
from automata_builder.ui.tab.components import (
    AutomataContainer,
    FunctionInput,
    LengthInput,
    Parameters,
    Points,
    SidePanel,
)
from automata_builder.utiles.utiles import (
    StoppableFunction,
    WorkerThread,
    generate_colors,
)


class Tab(QWidget):
    DEFUALT_LENGTH = 10

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.automata_container = AutomataContainer()
        self.automata_container.setMinimumWidth(self.width() // 4)
        self.automata_container.setMinimumHeight(self.height() // 3)
        self.automata_container.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.automata_container.set_automata_errors_handler(self.show_errors)

        self.params_input = Parameters(self.word_input_condition)
        self.params_input.setMaximumHeight(int(0.94 * self.height()))
        self.params_input.setMaximumWidth(self.width() // 4)
        self.params_input.setMinimumWidth(0)

        self.params_input.draw_button.clicked.connect(self.draw_automata_click)
        self.params_input.draw_curves_button.clicked.connect(self.draw_curves_click)
        self.params_input.verify_button.clicked.connect(self.verify_click)

        self.func_input = FunctionInput()
        self.func_input.setMaximumWidth(self.width() // 4)
        self.func_input.setMinimumWidth(0)
        self.func_input.setFixedHeight(150)
        self.func_input.draw_button.clicked.connect(self.draw_func_click)

        self.errors_panel_width_ = self.width() // 3
        self.plot_panel_width_ = self.height()
        side_panel_max_width = max(self.plot_panel_width_, self.errors_panel_width_)

        self.length_input = LengthInput(default_len=Tab.DEFUALT_LENGTH)

        self.stop_button = QPushButton("Stop drawing")
        self.stop_button.clicked.connect(self.stop_computation)

        self.mid_panel__layout = QVBoxLayout()
        self.mid_panel__layout.addWidget(self.length_input)
        self.mid_panel__layout.addWidget(
            self.params_input, 1, Qt.AlignmentFlag.AlignTop
        )
        self.mid_panel__layout.addWidget(self.func_input, 1, Qt.AlignmentFlag.AlignTop)
        self.mid_panel__layout.addWidget(self.stop_button)

        self.side_panel = SidePanel()
        self.side_panel.setMaximumWidth(side_panel_max_width)
        self.side_panel.setMinimumWidth(0)
        self.side_panel.close_button.clicked.connect(self.close_panel_click)

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.addWidget(self.automata_container, 2)
        self._layout.addLayout(self.mid_panel__layout, 0)
        self._layout.addWidget(self.side_panel, 0)

        self.prev_prefix_text = self.params_input.prefix_field.text()
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)

        self._thread = None

    def automata(self) -> Automata | None:
        """Return automata or show errors and return None if automata is incorrect"""
        automata, errors = self.automata_container.automata()
        if automata is None:
            self.show_errors(errors)
            return

        errors = self.compare_params(
            automata.input_alphabet,
            automata.output_alphabet,
            automata.initial_state,
        )
        if len(errors) == 0:
            return automata

    def is_panel_hidden(self) -> bool:
        return self.side_panel.width() == 0

    def verify_click(self) -> None:
        automata = self.automata()
        if not automata:
            return

        self.params_input.load_data(
            automata.input_alphabet,
            automata.output_alphabet,
            automata.initial_state,
        )
        QMessageBox.information(self, "Notification", "Automata is correct")

    def draw_curves_click(self) -> None:
        automata = self.automata()
        if not automata:
            return

        inputs = sorted(automata.inputs, key=lambda x: automata.inputs[x])

        def calc(cond: Event):
            plots = []
            x, y = [], []
            xlim = 1, 2
            ylim = 1, len(automata.outputs) + 1

            colors = generate_colors(len(inputs))
            n = len(automata.states)

            for symb in inputs:
                word = symb * n
                for i in range(1, n + 1):
                    if cond.is_set():
                        return tuple(plots)
                    out_word = automata.read(word[:i])
                    x.append(2 * (1 - 2**-i))
                    y.append(automata.output_number(out_word))
                plots.append(Points(x, y, xlim, ylim, color=next(colors), is_plot=True))

            return tuple(plots)

        self.start_computation(calc)

    def draw_automata_click(self) -> None:
        automata = self.automata()
        if not automata:
            return

        input_alphabet = self.params_input.input_alphabet()
        output_alphabet = self.params_input.output_alphabet()

        # Check order of symbols
        # if orders is different then reset it
        if automata.input_alphabet != input_alphabet and len(input_alphabet) != 0:
            automata.reset_inputs_order(input_alphabet)

        if automata.output_alphabet != output_alphabet and len(input_alphabet) != 0:
            automata.reset_outputs_order(output_alphabet)

        self.params_input.load_data(
            automata.input_alphabet,
            automata.output_alphabet,
            automata.initial_state,
        )

        prefix = self.params_input.prefix()
        suffix = self.params_input.suffix()
        last_state = self.params_input.last_state()
        if last_state and last_state not in automata.states:
            self.show_errors(["Incorrect last state"])
            return

        length = self.length_input.get_length()

        compute_func = compute.by_automata(automata, length, prefix, suffix, last_state)
        self.start_computation(compute_func)

    def draw_func_click(self):
        base = self.func_input.get_base()
        try:
            func = self.func_input.get_function(base)
        except (SyntaxError, TypeError, ValueError) as e:
            QMessageBox.warning(self, "Invalid function", str(e))
            return

        length = self.length_input.get_length()
        self.start_computation(compute.by_function(func, base, length))

    def start_computation(self, func: StoppableFunction[None, Points]):
        if self._thread and self._thread.isRunning():
            reply = QMessageBox.question(
                self,
                "Confirm",
                "Do you want to stop computation? (default No)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.stop_computation()

        self._thread = WorkerThread(func)
        self._thread.setObjectName("computation thread")
        self._thread.result_ready.connect(lambda data: self.draw_plot(*data))
        self._thread.finished.connect(self._thread.deleteLater)

        def on_destroyed(_):
            self._thread = None

        self._thread.destroyed.connect(on_destroyed)

        self._thread.start()

    def stop_computation(self) -> None:
        if self._thread is None or self._thread.isFinished():
            return
        self._thread.stop()

    def draw_plot(self, *points: Points) -> None:
        if self.side_panel.current_mode != SidePanel.Mode.PLOT:
            self.side_panel.switch_to_plot()

        if not self.is_panel_hidden():
            self.side_panel.draw_plot(*points)
            return

        def after_finish():
            self.side_panel.draw_plot(*points)

        self.toggle_panel(self.plot_panel_width_, after_finish)

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
        errors = self.compare_params(
            automata.input_alphabet,
            automata.output_alphabet,
            automata.initial_state,
        )
        return len(errors) == 0 and symbols.issubset(automata.input_alphabet)

    def compare_params(
        self, input_alphabet: list[str], output_alphabet: list[str], initial_state: str
    ) -> list[str]:
        entered_input_alphabet = self.params_input.input_alphabet()
        entered_output_alphabet = self.params_input.output_alphabet()
        entered_initial_state = self.params_input.initial_state()

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

        self.toggle_panel(self.errors_panel_width_, after_finish)

    def toggle_panel(
        self, dest_width: int = 0, after_finish: Callable[[], None] | None = None
    ) -> None:
        group = QSequentialAnimationGroup(self.parentWidget())
        duration = 200

        auto_geom = self.automata_container.geometry()
        data_geom = self.params_input.geometry()
        panel_geom = self.side_panel.geometry()

        dest_auto_geom = QRect(self.automata_container.geometry())
        dest_data_geom = QRect(self.params_input.geometry())
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

        data_anim = QPropertyAnimation(self.params_input, b"geometry")
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
            i = self._layout.indexOf(self.side_panel)
            j = self._layout.indexOf(self.automata_container)
            if width_diff > 0:
                self.side_panel.setMaximumWidth(dest_width)
                self._layout.setStretch(i, 2)
                self._layout.setStretch(j, 1)
            else:
                self._layout.setStretch(i, 0)
                self._layout.setStretch(j, 2)

            if after_finish:
                after_finish()

        group.finished.connect(on_finish)

        group.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)

    def load(self, data: dict) -> None:
        params_data = data["params"]
        self.params_input.load_data(
            params_data["input_alphabet"],
            params_data["output_alphabet"],
            params_data["initial_state"],
        )
        self.params_input.load_draw_filters(
            params_data["prefix"],
            params_data["suffix"],
            params_data["last_state"],
        )

        if "function" in data:
            func_data = data["function"]
            self.func_input.load(
                func_data["function"],
                func_data["base"],
            )

        if "length" in data:
            self.length_input.load(data["length"])

        scene = self.automata_container.view.scene()
        scene.deserialize(data["scene"])

    def dump(self) -> dict:
        params_data = {
            "input_alphabet": self.params_input.input_alphabet(),
            "output_alphabet": self.params_input.output_alphabet(),
            "initial_state": self.params_input.initial_state(),
            "prefix": self.params_input.prefix(),
            "suffix": self.params_input.suffix(),
            "last_state": self.params_input.last_state(),
        }
        function_data = {
            "function": self.func_input.get_function_text(),
            "base": self.func_input.get_base(),
        }
        scene = self.automata_container.view.scene()
        return {
            "scene": scene.serialize(),
            "params": params_data,
            "function": function_data,
            "length": self.length_input.get_length(),
        }

    def is_empty(self):
        return self.automata_container.is_empty_scene() or self.params_input.is_empty()
