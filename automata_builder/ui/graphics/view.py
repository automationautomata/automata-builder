import json
import os
from typing import Optional

import PyQt6.QtGui as qtg
import PyQt6.QtWidgets as qtw
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtSvg import QSvgGenerator

from automata_builder.ui.common import (
    OverlayWidget,
    TableInputDialog,
    VerticalInputDialog,
)
from automata_builder.ui.graphics.items import Edge, Node
from automata_builder.utiles import utiles
from automata_builder.utiles.data import AUTOMATA_EXT, DATA_DIR, VIEW_FILE_NAME


class EdgeEditDialog(TableInputDialog):
    def __init__(self, edge: Edge, title: str = "") -> None:
        self.transitions = []
        for out_ in edge.outputs():
            for in_ in edge.input(out_):
                self.transitions.append([in_, out_])

        row_labels = [[f"{r[0]}:", f"{r[1]}:"] for r in self.transitions]
        super().__init__(*row_labels, col_titles=["Вход", "Выход"], title=title)

        for i in range(len(self.transitions)):
            delete_button = qtw.QPushButton("Удалить")
            delete_button.clicked.connect(lambda: self.delete_transition(delete_button))
            self.grid_layout.addWidget(delete_button, i + 1, 2)

    def fill_empty_row(self, row_ind: int) -> None:
        row_count = self.grid_layout.rowCount()
        for i in range(row_ind + 1, row_count):
            item = self.grid_layout.itemAtPosition(i, 0)
            widget = item.widget()
            self.grid_layout.removeWidget(widget)
            self.grid_layout.addWidget(widget, i, 0)

    def delete_transition(self, delete_button: qtw.QPushButton) -> None:
        index = self.grid_layout.indexOf(delete_button)
        row_ind, _, _, _ = self.grid_layout.getItemPosition(index)

        in_edit, out_edit = self.line_edits.pop(row_ind - 1)
        in_label, out_label = self.labels.pop(row_ind - 1)

        # Input
        item = self.grid_layout.itemAtPosition(row_ind, 0)
        layout = item.layout()
        self.grid_layout.removeItem(item)
        in_label.deleteLater()
        in_edit.deleteLater()
        del layout

        # Output
        item = self.grid_layout.itemAtPosition(row_ind, 1)
        layout = item.layout()
        self.grid_layout.removeItem(item)
        out_label.deleteLater()
        out_edit.deleteLater()
        del layout

        # Button
        self.grid_layout.removeWidget(delete_button)
        delete_button.deleteLater()

        # Lower rows move up
        self.fill_empty_row(row_ind)

        # Remove from transitions
        self.transitions.pop(row_ind - 1)

    def get_values(self) -> list[list[str]]:
        values = super().get_values()

        if len(self.transitions) == 0:
            return []

        if not values:
            return self.transitions

        for i in range(len(values)):
            if not values[i][0]:
                values[i][0] = self.transitions[i][0]

            if not values[i][1]:
                values[i][1] = self.transitions[i][1]

        return values


class BuildingScene(qtw.QGraphicsScene):
    INITIAL_STATE_COLOR = qtg.QColor(128, 25, 90, 180)

    def __init__(self, parent: Optional[qtw.QWidget] = None) -> None:
        super().__init__(parent)

        self.nodes: dict[str, Node] = {}  # словарь имя-узел
        self.edges: list[Edge] = []
        self.initial_state: Node = None
        self.marked_nodes_: list[Node] = []
        self.selected_nodes: list[Node] = []  # Nodes for connection
        # self.customContextMenuRequested.connect(self.context_menu)

    @property
    def marked_nodes(self) -> list[str]:
        return [n.name for n in self.marked_nodes_]

    def keyPressEvent(self, event: qtg.QKeyEvent | None) -> None:
        key = event.key()
        modifier = event.modifiers()
        if key == Qt.Key.Key_Delete:
            selected = self.selectedItems()

            selected_edges = [item for item in selected if isinstance(item, Edge)]
            while len(selected_edges) > 0:
                self.delete_edge(selected_edges.pop())

            selected_nodes = [item for item in selected if isinstance(item, Node)]
            while len(selected_nodes) > 0:
                self.delete_node(selected_nodes.pop())

        if key == Qt.Key.Key_A and modifier == Qt.KeyboardModifier.ControlModifier:
            self.select_all()

        return super().keyPressEvent(event)

    def mouseDoubleClickEvent(self, event: qtw.QGraphicsSceneMouseEvent | None) -> None:
        scene_pos = event.scenePos()
        items = self.items(scene_pos)
        if len(items) == 0:
            # Клик по пустому месту — добавляем новый узел в место клика
            name = f"S{len(self.nodes)}"
            new_node = Node(name, scene_pos.x(), scene_pos.y())
            self.addItem(new_node)
            self.nodes[name] = new_node
        return super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event: qtw.QGraphicsSceneContextMenuEvent) -> None:
        point = event.scenePos()
        items = self.items(point)
        if len(items) != 1:
            return
        item = items[0]
        menu = qtw.QMenu(self.parent())

        # Add actions to the menu
        if isinstance(item, Node):
            menu.addActions(self.node_actions(item))
        elif isinstance(item, Edge):
            menu.addActions(self.edge_actions(item))

        # Menu at cursor position
        menu.exec(event.screenPos())

    def node_actions(self, node: Node) -> list[qtg.QAction]:
        def edit_node():
            dialog = VerticalInputDialog("New name:")
            values = dialog.get_values()
            if not values:
                return

            new_name = values[0]
            if new_name != node.name and new_name in self.nodes:
                qtw.QMessageBox.warning(
                    self, "Ошибка", "Узел с таким названием уже существует"
                )
                return
            self.nodes.pop(node.name)
            node.name = new_name
            self.nodes[new_name] = node

        selected = self.selectedItems()
        selected_nodes = [item for item in selected if isinstance(item, Node)]
        if len(selected_nodes) > 2:
            return []

        delete_action = qtg.QAction("Удалить", self)
        delete_action.triggered.connect(lambda: self.delete_node(node))

        edit_action = qtg.QAction("Редактировать", self)
        edit_action.triggered.connect(edit_node)

        if self.initial_state is node:
            initial_action = qtg.QAction("Сделать обычным", self)
            initial_action.triggered.connect(lambda: self.unset_initial_node(node))
        else:
            initial_action = qtg.QAction("Сделать начальным", self)
            initial_action.triggered.connect(lambda: self.set_initial_node(node))

        actions = [delete_action, edit_action, initial_action]

        if len(selected_nodes) == 0 or len(selected_nodes) == 1:
            if not node.has_loop():
                make_loop_action = qtg.QAction("Сделать петлю", self)
                make_loop_action.triggered.connect(lambda: self.create_edge(node, node))
                actions.append(make_loop_action)
            return actions

        src: Node = (
            selected_nodes[0] if selected_nodes[0] is not node else selected_nodes[1]
        )
        if src.name not in node.in_edges:
            add_edge_action = qtg.QAction("Соединить", self)
            add_edge_action.triggered.connect(lambda: self.create_edge(src, node))
            actions.append(add_edge_action)

        return actions

    def edge_actions(self, edge: Edge) -> list[qtg.QAction]:
        def edit_edge():
            dialog = EdgeEditDialog(edge, "Редактирование")
            values = dialog.get_values()
            if not values:
                return

            if len(values) == 0:
                self.delete_edge(edge)
                return

            edge.transitions = {}
            for in_, out_ in values:
                edge.add_transition(out_, in_)

        def new_transition():
            values = self.enter_edge()
            if not values or not (values[0] and values[1]):
                return
            in_, out_ = values
            edge.add_transition(out_, in_)

        delete_action = qtg.QAction("Удалить", self)
        edit_action = qtg.QAction("Редактировать", self)
        add_action = qtg.QAction("Добавить", self)

        delete_action.triggered.connect(lambda: self.delete_edge(edge))
        edit_action.triggered.connect(edit_edge)
        add_action.triggered.connect(new_transition)

        return [delete_action, edit_action, add_action]

    def create_edge(self, source: Node, destination: Node) -> None:
        values = self.enter_edge()
        if not values or not (values[0] and values[1]):
            return

        in_, out_ = values
        edge = Edge(in_, out_, source, destination)

        # Добавляем линию на сцену и в списки связных узлов
        source.out_edges[destination.name] = edge
        destination.in_edges[source.name] = edge
        self.edges.append(edge)

        self.addItem(edge)
        edge.update_path()

    def delete_node(self, node: Node) -> None:
        if node.has_loop():
            edge = node.in_edges.pop(node.name)
            self.delete_edge(edge)

        for src_node in list(node.in_edges.keys()):
            # Удаляем текущий узел (приемник)
            # из списка ребер узла, из которого оно исходит
            edge = node.in_edges.pop(src_node)

            # Удаляем само реберо
            self.delete_edge(edge)

        for dst_node in list(node.out_edges.keys()):
            # Удаляем текущий узел (источник)
            # из списка ребер узла, в которое ребро входит
            edge = node.out_edges.pop(dst_node)

            # Удаляем само реберо
            self.delete_edge(edge)

        # Удаляем узел реберо
        self.nodes.pop(node.name)
        self.removeItem(node)
        del node

    def delete_edge(self, edge: Edge) -> None:
        edge.source.out_edges.pop(edge.destination.name)
        edge.destination.in_edges.pop(edge.source.name)

        self.removeItem(edge)
        self.edges.pop(self.edges.index(edge))
        del edge

    def set_initial_node(self, node: Node) -> Node:
        if self.initial_state:
            self.initial_state.setBrush(qtg.QBrush(node.COLOR))
        self.initial_state = node
        node.setBrush(self.INITIAL_STATE_COLOR)

    def unset_initial_node(self, node: Node) -> Node:
        if self.initial_state:
            self.initial_state.setBrush(qtg.QBrush(node.COLOR))
        self.initial_state = None

    @staticmethod
    def enter_edge() -> list[str]:
        input_field = VerticalInputDialog("Вход", "Выход:")
        return input_field.get_values()

    def select_all(self) -> None:
        for node in self.nodes.values():
            node.setSelected(True)
        for edge in self.edges:
            edge.setSelected(True)

    def mark_node(self, node_name: str, color: qtg.QColor) -> None:
        if node_name not in self.nodes:
            raise ValueError()
        node = self.nodes[node_name]
        brush = node.brush()
        brush.setColor(color)
        node.setBrush(brush)
        if node not in self.marked_nodes_:
            self.marked_nodes_.append(node)

    def unmark_node(self, node_name: str) -> None:
        if node_name not in self.nodes:
            raise ValueError()
        node = self.nodes[node_name]
        brush = node.brush()
        if node is not self.initial_state:
            brush.setColor(node.COLOR)
        else:
            brush.setColor(self.INITIAL_STATE_COLOR)
        node.setBrush(brush)

        if node in self.marked_nodes_:
            self.marked_nodes_.remove(node)

    def serialize(self) -> str:
        initial_state = ""
        if self.initial_state:
            initial_state = self.initial_state.name

        rect = self.sceneRect()

        return {
            "nodes": [node.serialize() for node in self.nodes.values()],
            "edges": [edge.serialize() for edge in self.edges],
            "initial_state": initial_state,
            "scene_rect": {
                "left": rect.left(),
                "top": rect.top(),
                "width": rect.width(),
                "height": rect.height(),
            },
        }

    def deserialize(self, data: dict) -> None:
        if "scene_rect" in data:
            rect = data["scene_rect"]
            self.setSceneRect(
                QRectF(rect["left"], rect["top"], rect["width"], rect["height"])
            )
        # Восстановливаем узлы по именам
        self.nodes = {}
        for node_data in data["nodes"]:
            node = Node.deserialize(node_data)
            self.nodes[node.name] = node
            self.addItem(node)

        # Восстановливаем ребра
        self.edges = []
        for edge_data in data["edges"]:
            edge = Edge.deserialize(edge_data, self.nodes)
            self.edges.append(edge)
            self.addItem(edge)
            edge.update_path()

        if data["initial_state"]:
            name = data["initial_state"]
            self.set_initial_node(self.nodes[name])

    def clear(self) -> None:
        super().clear()
        self.initial_state = None
        self.marked_nodes_ = []
        self.selected_nodes = []
        self.nodes = {}
        self.edges = []


class BuilderView(qtw.QGraphicsView):
    def __init__(
        self, parent: Optional[qtw.QWidget] = None, button_size: int = 40
    ) -> None:
        super().__init__(parent)
        self.scene_ = BuildingScene(self)
        self.setScene(self.scene_)

        self.overlay_container = OverlayWidget(self)
        self.overlay_container.setContentsMargins(0, 0, 0, 0)

        self.save_button = qtw.QPushButton("Save")
        self.save_button.setFixedSize(button_size, button_size // 2)
        self.save_button.clicked.connect(self.save_view)

        self.load_button = qtw.QPushButton("Load")
        self.load_button.setFixedSize(button_size, button_size // 2)
        self.load_button.clicked.connect(self.load_view)

        self.svg_export_button = qtw.QPushButton("Export to svg")
        self.svg_export_button.setMinimumSize(button_size, button_size // 2)
        self.svg_export_button.clicked.connect(self.save_svg)

        buttons_layout = qtw.QHBoxLayout()
        buttons_layout.addWidget(self.load_button)
        buttons_layout.addWidget(self.save_button)
        buttons_layout.addWidget(self.svg_export_button)
        self.overlay_container.setLayout(buttons_layout)

        self.setRenderHints(
            qtg.QPainter.RenderHint.Antialiasing
            | qtg.QPainter.RenderHint.TextAntialiasing
            | qtg.QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setDragMode(qtw.QGraphicsView.DragMode.ScrollHandDrag)
        self.setResizeAnchor(qtw.QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setTransformationAnchor(qtw.QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.viewport().setCursor(Qt.CursorShape.ArrowCursor)

    @property
    def marked_nodes(self) -> list[str]:
        return self.scene_.marked_nodes_

    def mousePressEvent(self, event: qtg.QMouseEvent | None) -> None:
        super().mousePressEvent(event)
        # После начала перетаскивания вернуть курсор стрелки
        self.viewport().setCursor(Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self, event: qtg.QMouseEvent | None) -> None:
        super().mouseReleaseEvent(event)
        # После отпускания кнопки вернуть курсор стрелки
        self.viewport().setCursor(Qt.CursorShape.ArrowCursor)

    def mouseDoubleClickEvent(self, event: qtg.QMouseEvent | None) -> None:
        super().mouseDoubleClickEvent(event)
        self.viewport().setCursor(Qt.CursorShape.ArrowCursor)

    def wheelEvent(self, event: qtg.QWheelEvent | None) -> None:
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            zoom_direction = event.angleDelta().y() > 0
            self.zoom_scene(zoom_direction, event.position())
        return super().wheelEvent(event)

    def resizeEvent(self, event: qtg.QResizeEvent | None):
        self.setSceneRect(self.scene_.itemsBoundingRect())
        super().resizeEvent(event)

    def zoom_scene(
        self, zoom_direction: bool, pos: QPointF, zoom_in_factor: float = 1.25
    ) -> None:
        """If zoom_direction is True then the scene is zoomed in else zoomed out"""

        # Save the scene position under mouse
        old_pos = self.mapToScene(pos.toPoint())

        # Determine zoom factor based on wheel direction
        zoom_factor = zoom_in_factor if zoom_direction else 1 / zoom_in_factor

        # Apply scaling
        self.blockSignals(True)
        self.scale(zoom_factor, zoom_factor)
        self.blockSignals(False)
        # Get new position after scaling
        new_pos = self.mapToScene(pos.toPoint())

        # Move view to keep mouse position stable
        delta = new_pos - old_pos
        self.translate(delta.x(), delta.y())

    def mark_node(self, node_name: str, color: qtg.QColor) -> None:
        self.scene_.mark_node(node_name, color)

    def unmark_node(self, node_name: str) -> None:
        self.scene_.unmark_node(node_name)

    def mark_all(self, color: qtg.QColor) -> None:
        for node in self.scene_.nodes:
            self.scene_.mark_node(node, color)

    def unmark_all(self) -> None:
        marked_nodes = self.scene_.marked_nodes.copy()
        for node in marked_nodes:
            self.scene_.unmark_node(node)

    def save_view(self) -> None:
        file_path, _ = qtw.QFileDialog.getSaveFileName(
            self,
            "Сохранить файл",
            DATA_DIR,
            f"Файлы (*.{AUTOMATA_EXT});;All Files (*)",
        )
        if not file_path:
            return
        path, filename = os.path.split(file_path)
        try:
            utiles.save_json(self.scene_.serialize(), path, filename)
        except (OSError, IOError):
            qtw.QMessageBox.warning(self, "Error", "Automata save failed")
            return
        qtw.QMessageBox.information(self, "Notification", "saved")

    def load_view(self) -> None:
        file_path, _ = qtw.QFileDialog.getOpenFileName(
            self,
            "Выберите файл",
            DATA_DIR,
            f"Файлы (*.{AUTOMATA_EXT});;All Files (*)",
        )
        if not file_path:
            return

        try:
            self.clear_scene()
            with open(file_path, mode="r") as file:
                self.scene_.deserialize(json.loads(file.read()))
        except IOError:
            qtw.QMessageBox.warning(self, "Error", "Automata save failed")
        except (json.JSONDecodeError, TypeError):
            qtw.QMessageBox.warning(self, "Error", "File incorrect format")
        else:
            qtw.QMessageBox.information(self, "Notification", "loaded")

    def save_svg(self) -> None:
        start_path = os.path.join(DATA_DIR, VIEW_FILE_NAME)
        file_path, _ = qtw.QFileDialog.getSaveFileName(
            self,
            "Save File",
            start_path,
            "Text Files (*.svg);;All Files (*)",  # file filters
        )
        if not file_path:
            return
        try:
            selected = self.scene_.selectedItems()
            self.scene_.clearSelection()

            scene_rect = self.scene_.itemsBoundingRect()
            # if scene_rect.isEmpty():
            #     scene_rect = self.scene_.sceneRect()

            generator = QSvgGenerator()
            generator.setFileName(file_path)
            generator.setSize(self.scene_.sceneRect().size().toSize())
            generator.setViewBox(scene_rect)

            painter = qtg.QPainter()
            painter.begin(generator)
            painter.setFont(Node.FONT)
            self.scene_.render(
                painter,
                self.scene_.sceneRect(),
                self.scene_.sceneRect(),
                mode=Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            )
            painter.end()

            for item in selected:
                item.setSelected(True)
        except IOError:
            qtw.QMessageBox.warning(self, "Error", "Automata save failed")

    def initial_state(self) -> str:
        initial_state = self.scene_.initial_state
        return initial_state.name if initial_state else ""

    def get_transitions_table(self) -> dict[str, list]:
        scene = self.scene_

        transitions = {}
        for src_name, node in scene.nodes.items():
            transitions[src_name] = []
            for dest_name, edge in node.out_edges.items():
                for out_ in edge.outputs():
                    transitions[src_name].extend(
                        (in_, dest_name) for in_ in edge.input(out_)
                    )

        return transitions

    def get_outputs_table(self) -> dict[str, list]:
        scene = self.scene_

        outputs_table = {}
        for src_name, node in scene.nodes.items():
            outputs_table[src_name] = []
            for edge in node.out_edges.values():
                for out_ in edge.outputs():
                    outputs_table[src_name].extend(
                        (in_, out_) for in_ in edge.input(out_)
                    )
        return outputs_table

    def is_empty(self):
        return len(self.scene_.items()) == 0

    def clear_scene(self) -> None:
        self.scene().clear()

    # def resizeEvent(self, event: QResizeEvent | None) -> None:
    #     old_size, new_size = event.oldSize(), event.size()
    #     self.blockSignals(True)
    #     old_ratio, new_ratio = (
    #         math.sqrt(old_size.width() ** 2 + old_size.height()),
    #         math.sqrt(new_size.width() ** 2 + new_size.height()),
    #     )
    #     diff = old_size - new_size
    #     self.zoom_scene(
    #         diff.width() < 0, self.sceneRect().center(), old_ratio/new_ratio
    #     )
    #     self.blockSignals(False)
    #     return super().resizeEvent(event)
