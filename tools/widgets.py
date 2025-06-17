from typing import Callable

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QGraphicsTextItem,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from lang import getstr


class MultipleInputDialog(QDialog):
    labels: list[QLabel]
    line_edits: list[QLineEdit]

    def __init__(self, title: str = "") -> None:
        super().__init__(parent=QApplication.activeWindow())
        self.setWindowTitle(title)

        self.container = QWidget()
        layout = QVBoxLayout()

        button_layout = QHBoxLayout()
        ok_button = QPushButton(getstr("accept"), self)
        cancel_button = QPushButton(getstr("cancel"), self)

        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)

        layout.addWidget(self.container)
        layout.addLayout(button_layout)
        self.setLayout(layout)

    def get_values(self) -> list[str] | None:
        if not self.exec():
            return None
        try:
            values = [le.text() for le in self.line_edits]
            if any(values):
                return values
        except ValueError:
            return None


class VerticalInputDialog(MultipleInputDialog):
    def __init__(self, *labels: str, title: str = "") -> None:
        super().__init__(title)

        layout = QVBoxLayout(self)
        n = len(labels)
        self.labels = [None] * n
        self.line_edits = [None] * n

        for i, label in enumerate(labels):
            self.labels[i] = QLabel(label, self)
            self.line_edits[i] = QLineEdit(self)
            layout.addWidget(self.labels[i])
            layout.addWidget(self.line_edits[i])

        self.container.setLayout(layout)


class TableInputDialog(MultipleInputDialog):
    labels: list[list[QLabel]]
    line_edits: list[list[QLineEdit]]

    def __init__(
        self,
        *row_labels: list[str],
        col_titles: list[str] | None = None,
        title: str = "",
    ) -> None:
        super().__init__(title)

        self.labels = [None] * len(row_labels)
        self.line_edits = [None] * len(row_labels)

        self.grid_layout = QGridLayout()

        start = 0
        if col_titles:
            for j, title in enumerate(col_titles):
                self.grid_layout.addWidget(QLabel(title), start, j)
            start += 1

        for i, row in enumerate(row_labels):
            self.labels[i] = []
            self.line_edits[i] = []
            for j, label in enumerate(row):
                row_layout = QHBoxLayout()

                self.labels[i].append(QLabel(label))
                self.line_edits[i].append(QLineEdit())

                row_layout.addWidget(self.labels[i][j])
                row_layout.addWidget(self.line_edits[i][j])

                self.grid_layout.addLayout(row_layout, i + start, j)

        self.container.setLayout(self.grid_layout)

    def get_values(self) -> list[list[str]]:
        if not self.exec():
            return None
        try:
            values = [[edit.text() for edit in row] for row in self.line_edits]

            if any(any(row) for row in values):
                return values

            return None
        except ValueError:
            return None


class EditableTextItem(QGraphicsTextItem):
    def __init__(self, text, parent, handler: Callable[[str], None] = None):
        super().__init__(text, parent)
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.setFlags(
            # QGraphicsTextItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsTextItem.GraphicsItemFlag.ItemIsFocusable
        )


class VerticalMessagesWidget(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.main_layout = QVBoxLayout(self)

        # Создаём область с прокруткой
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        # Внутренний контейнер для сообщений
        self.messages_container = QWidget()

        self.messages_layout = QVBoxLayout()
        self.messages_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.messages_layout.setDirection(QVBoxLayout.Direction.Down)
        self.messages_container.setLayout(self.messages_layout)

        self.scroll_area.setWidget(self.messages_container)

        # Добавляем область прокрутки в основной макет
        self.main_layout.addWidget(self.scroll_area)

        # Храним список сообщений для обновления ширины при ресайзе
        self.labels: list[QLabel] = []

    @property
    def count(self) -> int:
        return len(self.labels)

    @property
    def scrollbar(self) -> int:
        return self.scroll_area.verticalScrollBar()

    @property
    def container(self) -> QWidget:
        return self.messages_container

    def add_message(self, text: str) -> None:
        label = QLabel(text)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        label.setWordWrap(True)

        self.messages_layout.addWidget(label)
        self.labels.append(label)

        scrollbar = self.scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def get_message(self, message_pos: int) -> QLabel:
        return self.labels[message_pos]

    def remove_message(self, message_pos: int) -> None:
        if message_pos > len(self.labels):
            raise ValueError(
                "The message position must be less than the number of messages"
            )
        label = self.labels[message_pos]
        self.layout().removeWidget(label)
        self.labels.pop(message_pos)
        label.deleteLater()

    def clear(self) -> None:
        while len(self.labels) > 0:
            label = self.labels.pop()
            self.layout().removeWidget(label)
            label.deleteLater()


class PlotWidget(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def draw(self, x: list[int], y: list[int], title: str = "Embedded Matplotlib Plot"):
        ax = self.figure.add_subplot(1, 1, 1)
        ax.plot(x, y)
        ax.set_title(title)
        self.canvas.draw()
