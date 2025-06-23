from typing import Callable
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QGraphicsTextItem,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)

from lang import getlocale


class MultipleInputDialog(QDialog):
    labels: list[QLabel]
    line_edits: list[QLineEdit]

    def __init__(self, title: str = "") -> None:
        super().__init__(parent=QApplication.activeWindow())
        self.setWindowTitle(title)

        self.container = QWidget()
        layout = QVBoxLayout()

        button_layout = QHBoxLayout()
        ok_button = QPushButton(getlocale("accept"), self)
        cancel_button = QPushButton(getlocale("cancel"), self)

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
    def __init__(self, text: str = "", parent: QWidget | None = None):
        super().__init__(text, parent)
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.setFlags(
            # QGraphicsTextItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsTextItem.GraphicsItemFlag.ItemIsFocusable
        )

    def keyPressEvent(self, event: QKeyEvent | None) -> None:
        if event.key() == Qt.Key.Key_Enter:
            self.disable_edit()
        return super().keyPressEvent(event)

    def enable_edit(self) -> None:
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
        self.setFocus()

    def disable_edit(self) -> None:
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.clearFocus()


class VerticalMessagesWidget(QListWidget):
    def __init__(self, parent: QWidget | None = None, spacing: int = 2) -> None:
        super().__init__(parent)
        self.setSpacing(spacing)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSelectionMode(QListWidget.SelectionMode.NoSelection)

    def add_message(self, text: str) -> None:
        item = QListWidgetItem(self)
        label = QLabel(text)
        label.setContentsMargins(0, 0, 0, 0)
        label.setMaximumWidth(self.width())

        label.setWordWrap(True)
        self.addItem(item)
        self.setItemWidget(item, label)
        item.setSizeHint(label.sizeHint())

    def get_message(self, message_pos: int) -> QLabel:
        return self.itemWidget(self.item(message_pos))

    def remove_message(self, message_pos: int) -> None:
        if message_pos > self.count():
            raise ValueError(
                "The message position must be less than the number of messages"
            )
        
        message_item = self.item(message_pos)
        if not message_item:
            return
        
        message = self.itemWidget(message_item)
        if not message:
            return
        
        self.removeItemWidget(message_item)
        message.deleteLater()

        row = self.row(message_item)
        taken_item = self.takeItem(row)
        del taken_item

    def clear(self) -> None:
        while self.count() > 0:
            self.remove_message(self.count() - 1)


class PlotWidget(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def draw(
        self, x: list[int], y: list[int], title: str = "Embedded Matplotlib Plot"
    ) -> None:
        ax = self.figure.add_subplot(1, 1, 1)
        ax.plot(x, y)
        ax.set_title(title)
        self.canvas.draw()


class OverlayWidget(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)


class TableWidget(QTableWidget):
    def __init__(
        self,
        data: list,
        column_names: list[str] | None = None,
        row_names: list[str] | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        for i, row in enumerate(data):
            for j, item in enumerate(row):
                self.setItem(i, j, QTableWidgetItem(item))

        if row_names:
            self.setHorizontalHeaderLabels(row_names)
        if column_names:
            self.setVerticalHeaderLabels(column_names)

        self.horizontalHeader().setStretchLastSection(True)
        # self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
