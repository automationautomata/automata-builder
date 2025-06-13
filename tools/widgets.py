from typing import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QGraphicsTextItem,
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
    def __init__(
        self,
        *labels_: str,
        title: str = "",
    ):
        super().__init__(parent=QApplication.activeWindow())
        self.setWindowTitle(title)

        self.values = [None] * len(labels_)
        self.labels_ = [None] * len(labels_)
        self.line_edits = [None] * len(labels_)

        layout = QVBoxLayout(self)
        for i, label in enumerate(labels_):
            self.labels_[i] = QLabel(label, self)
            self.line_edits[i] = QLineEdit(self)
            layout.addWidget(self.labels_[i])
            layout.addWidget(self.line_edits[i])

        # Кнопки OK и Cancel
        button_layout = QHBoxLayout()
        ok_button = QPushButton(getstr("accept"), self)
        cancel_button = QPushButton(getstr("cancel"), self)

        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def getValues(self) -> tuple[str] | None:
        if self.exec():
            try:
                values = [le.text() for le in self.line_edits]
                if any(v for v in values):
                    return values
            except ValueError:
                # Обработка некорректных данных
                return None
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

    #     self.handler = handler

    # def set_handler(self, handler):
    #     self.handler = handler

    # def keyPressEvent(self, event):
    #     if event.key() in (Qt.Key.Key_Return.real, Qt.Key.Key_Enter.real):
    #         # Завершаем редактирование по Enter: снимаем фокус и отключаем редактирование
    #         self.clearFocus()
    #         self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
    #         self.handler(self.toPlainText())
    #     return super().keyPressEvent(event)

    # def mouseDoubleClickEvent(self, event):
    #     # При двойном клике включаем режим редактирования
    #     self.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
    #     self.setFocus()
    #     return super().mousePressEvent(event)


class VerticalMessagesWidget(QScrollArea):
    def __init__(
        self,
        parent: QWidget | None = None,
        *messages: tuple[str],
    ) -> None:
        super().__init__(parent)
        self.container = QWidget(self)

        self.setWidget(self.container)

        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        self.container_layout.setDirection(QVBoxLayout.Direction.Down)

        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.labels_: list[QLabel] = [None] * len(messages)
        for i, message in enumerate(messages):
            self.labels_[i] = QLabel(text=message)
            self.container_layout.addWidget(self.labels_[i])

            self.labels_[i].setWordWrap(True)
            self.labels_[i].adjustSize()
            self.labels_[i].setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
            )
            self.labels_[i].setScaledContents(True)
            self.labels_[i].setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
        self.verticalScrollBar().setMaximumWidth(7)

    def resizeEvent(self, a0) -> None:
        self.blockSignals(True)
        scrol_bar_width = self.verticalScrollBar().width()
        self.container.setMaximumWidth(self.width() - 2*scrol_bar_width)
        self.verticalScrollBar().setMaximumHeight(self.height())
        self.blockSignals(False)
        return super().resizeEvent(a0)

    @property
    def count(self) -> int:
        return len(self.labels_)

    def add_message(self, message: str) -> None:
        label = QLabel(text=message)
        self.container_layout.addWidget(label)
        self.labels_.append(label)
        
        label.adjustSize()
        label.setWordWrap(True)
        label.setScaledContents(True)
        
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        scrol_bar_width = self.verticalScrollBar().width()
        label.setMaximumWidth(self.width() - 2*scrol_bar_width)
        
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

    def get_message(self, message_pos: int) -> QLabel:
        return self.labels_[message_pos]

    def remove_message(self, message_pos: int) -> None:
        if message_pos > len(self.labels_):
            raise ValueError(
                "The message position must be less than the number of messages"
            )
        label = self.labels_[message_pos]
        self.layout().removeWidget(label)
        self.labels_.pop(message_pos)
        label.deleteLater()

    def clear(self) -> None:
        while len(self.labels_) >= 0:
            label = self.labels_.pop()
            self.layout().removeWidget(label)
            label.deleteLater()
