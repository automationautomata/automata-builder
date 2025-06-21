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

from automata import Automata
from tab.components import *  # noqa: F403


class AutomataTabWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.automata_container = AutomataContainer()
        self.automata_container.setMinimumWidth(self.width() // 4)
        self.automata_container.setMinimumHeight(self.height() // 3)
        self.automata_container.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        self.automata_data = AutomataDataWidget()
        self.automata_data.setMaximumHeight(2 * self.height() // 3)
        self.automata_data.setMaximumWidth(self.width() // 4)
        self.automata_data.setMinimumWidth(0)

        self.side_panel = SidePanel()
        # self.side_panel.sizeHint = lambda: QSize(0, self.height() // 3)
        # self.side_panel.setHidden(True)
        self.errors_panel_width = self.width() // 3
        self.plot_panel_width = self.width() // 3
        side_panel_max_width = max(self.plot_panel_width, self.errors_panel_width)
        self.side_panel.setMaximumWidth(side_panel_max_width)
        self.side_panel.setMinimumWidth(0)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.automata_container)
        main_layout.addWidget(self.automata_data, 0, Qt.AlignmentFlag.AlignTop)
        main_layout.addWidget(self.side_panel)

        self.automata_data.verify_button.clicked.connect(self.verify_click)
        self.automata_data.draw_button.clicked.connect(self.draw_click)
        self.side_panel.close_button.clicked.connect(self.close_panel_click)

        self.automata_container.set_automata_check(self.automata_errors_handler)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)

    def automata_errors_handler(self, automata: Automata) -> bool:
        errors = self.check_automata(automata)
        if len(errors) != 0:
            errors += [''.join(map(lambda x: '   ' if x % 10 == 1 else str(x) , range(100)))]
            errors += [''.join(map(lambda x: '   ' if x % 10 == 1 else str(x) , range(100)))]
            self.show_errors(errors)
            return False
        return True

    def is_panel_hidden(self) -> bool:
        return self.side_panel.width() == 0

    def verify_click(self) -> None:
        automata = self.automata_container.automata()
        if not self.automata_errors_handler(automata):
            return

        self.automata_data.set_data(
            automata.input_alphabet,
            automata.output_alphabet,
            automata.initial_state,
        )
        QMessageBox.information(self, "Notification", "Automata is correct")

    def draw_click(self) -> None:
        automata = self.automata_container.automata()
        if not self.automata_errors_handler(automata):
            return

        input_alphabet = self.automata_data.input_alphabet()
        output_alphabet = self.automata_data.output_alphabet()

        # Check order of symbols
        # if orders is different then reset it
        if automata.input_alphabet != input_alphabet and len(input_alphabet) != 0:
            automata.reset_input_order(input_alphabet)

        if automata.output_alphabet != output_alphabet and len(input_alphabet) != 0:
            automata.reset_output_order(output_alphabet)

        prec = 20
        x, y = [], []
        for i in range(prec):
            for in_word, out_word in automata.pairs_generator(i):
                x.append(automata.to_number(in_word))
                y.append(automata.to_number(out_word))

        if self.side_panel.current_mode != SidePanel.Mode.PLOT:
            self.side_panel.switch_to_plot()

        if not self.is_panel_hidden():
            self.side_panel.draw_plot(x, y)
            return

        def after_finish():
            return self.side_panel.draw_plot(x, y)

        self.show_panel(self.plot_panel_width, after_finish)

    def close_panel_click(self) -> None:
        if self.is_panel_hidden():
            return

        def after_finish():
            self.side_panel.switch_to_empty()
            self.side_panel.setSizePolicy(
                QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding
            )
            self.side_panel.setMinimumWidth(0)

        self.hide_panel(after_finish=after_finish)

    def check_automata(self, automata: Automata) -> list[str]:
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

        return automata.detailed_verificatin()

    def show_errors(self, errors: list[str]) -> None:
        if self.side_panel.current_mode == SidePanel.Mode.ERROR_MESSAGES:  # noqa: F405
            self.side_panel.clear_messages()
        else:
            self.side_panel.switch_to_messages()
            self.side_panel.clear_messages()

        if not self.is_panel_hidden():
            self.side_panel.add_messages(*errors)
            return

        def after_finish():
            self.side_panel.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            self.side_panel.add_messages(*errors)

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

        auto_geom = self.automata_container.geometry()
        data_geom = self.automata_data.geometry()
        panel_geom = self.side_panel.geometry()

        dest_auto_geom = QRect(self.automata_container.geometry())
        dest_data_geom = QRect(self.automata_data.geometry())
        dest_panel_geom = QRect(self.side_panel.geometry())

        dest_panel_geom.setWidth(dest_width)
        if flag:
            dest_panel_geom.setLeft(panel_geom.right() - dest_width)
            dest_panel_geom.setRight(panel_geom.right())

            dest_data_geom.setWidth(data_geom.width() - dest_width)
            dest_data_geom.setLeft(data_geom.left() - dest_width)
            dest_data_geom.setRight(data_geom.right() - dest_width)

            dest_auto_geom.setWidth(auto_geom.width() - dest_width)
            dest_auto_geom.setRight(auto_geom.right() - dest_width)
        else:
            dest_panel_geom.setLeft(panel_geom.right())
            dest_panel_geom.setRight(panel_geom.right())

            dest_data_geom.setWidth(data_geom.width() + panel_geom.width())
            dest_data_geom.setLeft(data_geom.left() + panel_geom.width())
            dest_data_geom.setRight(data_geom.right() + panel_geom.width())

            dest_auto_geom.setWidth(auto_geom.width() + panel_geom.width())
            dest_auto_geom.setRight(auto_geom.right() + panel_geom.width())

        auto_anim = QPropertyAnimation(self.automata_container, b"geometry", self)
        auto_anim.setDuration(duration // 8)
        auto_anim.setStartValue(self.automata_container.geometry())
        auto_anim.setEndValue(dest_auto_geom)
        auto_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

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

        if after_finish:
            group.finished.connect(after_finish)

        group.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
