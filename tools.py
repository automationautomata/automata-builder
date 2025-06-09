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
    QVBoxLayout,
)

from lang import getstr


class MultipleInputDialog(QDialog):
    def __init__(
        self,
        *labels: str,
        title: str = "",
    ):
        super().__init__(parent=QApplication.activeWindow())
        self.setWindowTitle(title)

        self.values = [None] * len(labels)
        self.labels = [None] * len(labels)
        self.line_edits = [None] * len(labels)

        layout = QVBoxLayout()
        for i, label in enumerate(labels):
            self.labels[i] = QLabel(label)
            self.line_edits[i] = QLineEdit()
            layout.addWidget(self.labels[i])
            layout.addWidget(self.line_edits[i])

        # Кнопки OK и Cancel
        button_layout = QHBoxLayout()
        ok_button = QPushButton(getstr("accept"))
        cancel_button = QPushButton(getstr("cancel"))
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
