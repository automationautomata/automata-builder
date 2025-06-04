from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QGraphicsSimpleTextItem,
    QGraphicsTextItem,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)


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
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Отмена")
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def getValues(self) -> tuple[str] | None:
        if self.exec():
            try:
                values = tuple(le.text() for le in self.line_edits)
                return values
            except ValueError:
                # Обработка некорректных данных
                return None
        return None


class EditableTextItem(QGraphicsSimpleTextItem):
    def __init__(self, text, parent):
        super().__init__(text, parent)
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.editor = None  # To hold the temporary editor

    def mousePressEvent(self, event):
        if not self.editor:
            # Create a QGraphicsTextItem for editing
            #self.toPlainText()
            self.editor = QGraphicsTextItem()
            self.editor.setParentItem(self)
            self.editor.setPos(0, 0)
            self.editor.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextEditorInteraction
            )
            self.editor.focusInEvent = self.focusInEvent
            # Connect focus out or key press to finish editing
            self.editor.focusOutEvent = self.finish_editing
        super().mousePressEvent(event)

    def focusInEvent(self, event):
        super().focusInEvent(event)

    def finish_editing(self, event):
        # Save edited text back to the simple text item
        new_text = self.editor.toPlainText()
        self.setText(new_text)
        # Remove the editor
        if self.editor:
            self.scene().removeItem(self.editor)
            self.editor = None
