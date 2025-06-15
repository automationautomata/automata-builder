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
        # scrollbar = self.scroll_area.verticalScrollBar()

        # Внутренний контейнер для сообщений
        self.messages_container = QWidget()
        # self.messages_container.setMinimumHeight(self.height())
        # self.messages_container.setMinimumWidth(self.width() - scrollbar.width())

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
        # label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        label.setWordWrap(True)

        self.messages_layout.addWidget(label)
        self.labels.append(label)

        scrollbar = self.scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def get_message(self, message_pos: int) -> QLabel:
        return self.labels[message_pos]

    def remove_message(self, message_pos: int) -> None:
        if message_pos > len(self.labels_):
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
