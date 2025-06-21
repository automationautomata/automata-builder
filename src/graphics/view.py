import json

from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QWheelEvent,
)
from PyQt6.QtWidgets import (
    QGraphicsScene,
    QGraphicsSceneContextMenuEvent,
    QGraphicsSceneMouseEvent,
    QGraphicsView,
    QMenu,
    QMessageBox,
    QPushButton,
    QWidget,
)

from automata import Automata
from graphics.items import Edge, Node
from widgets import (
    TableInputDialog,
    VerticalInputDialog,
)


class EdgeEditDialog(TableInputDialog):
    def __init__(self, edge: Edge, title: str = "") -> None:
        self.transitions = []
        for in_ in edge.inputs():
            for out_ in edge.output(in_):
                self.transitions.append([in_, out_])

        row_labels = [[f"{r[0]}:", f"{r[1]}:"] for r in self.transitions]
        super().__init__(*row_labels, col_titles=["Вход", "Выход"], title=title)

        for i in range(len(self.transitions)):
            delete_button = QPushButton("Удалить")
            delete_button.clicked.connect(lambda: self.delete_transition(delete_button))

            self.grid_layout.addWidget(delete_button, i + 1, 2)

    def fill_empty_row(self, row_ind: int) -> None:
        row_count = self.grid_layout.rowCount()
        for i in range(row_ind + 1, row_count):
            item = self.grid_layout.itemAtPosition(i, 0)
            widget = item.widget()
            self.grid_layout.removeWidget(widget)
            self.grid_layout.addWidget(widget, i, 0)

    def delete_transition(self, delete_button: QPushButton) -> None:
        row_ind, _, _, _ = self.grid_layout.getItemPosition(delete_button)

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
            return None

        for i in range(len(values)):
            if not values[i][0]:
                values[i][0] = self.transitions[i][0]

            if not values[i][1]:
                values[i][1] = self.transitions[i][1]

        return values


class AutomataDrawScene(QGraphicsScene):
    def __init__(self, parent: QWidget | None = None) -> None:
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

    def keyPressEvent(self, event: QKeyEvent | None) -> None:
        key_pressed = event.key()
        if key_pressed == Qt.Key.Key_Delete:
            selected = self.selectedItems()

            selected_nodes = [item for item in selected if isinstance(item, Node)]
            while len(selected_nodes) > 0:
                self.delete_node(selected_nodes.pop())

            selected_edges = [item for item in selected if isinstance(item, Edge)]
            while len(selected_edges) > 0:
                self.delete_edge(selected_edges.pop())

        return super().keyPressEvent(event)

    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent | None) -> None:
        scene_pos = event.scenePos()
        items = self.items(scene_pos)
        if len(items) == 0:
            # Клик по пустому месту — добавляем новый узел в место клика
            name = f"S{len(self.nodes)}"
            new_node = Node(name, scene_pos.x(), scene_pos.y())
            self.addItem(new_node)
            self.nodes[name] = new_node
        return super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event: QGraphicsSceneContextMenuEvent) -> None:
        point = event.scenePos()
        items = self.items(point)
        if len(items) != 1:
            return
        item = items[0]
        menu = QMenu(self.parent())

        # Add actions to the menu
        if isinstance(item, Node):
            menu.addActions(self.node_actions(item))
        elif isinstance(item, Edge):
            menu.addActions(self.edge_actions(item))

        # Отображаем меню в позиции курсора
        action = menu.exec(event.screenPos())
        # Можно проверить выбранное действие
        if action:
            print(f"Выбрано действие: {action.text()}")

    def node_actions(self, node: Node) -> list[QAction]:
        def edit_node():
            dialog = VerticalInputDialog("New name:")
            values = dialog.get_values()
            if not values:
                return

            new_name = values[0]
            if new_name != node.name and new_name in self.nodes:
                QMessageBox.warning(
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

        delete_action = QAction("Удалить", self)
        delete_action.triggered.connect(lambda: self.delete_node(node))

        edit_action = QAction("Редактировать", self)
        edit_action.triggered.connect(edit_node)

        make_initial_action = QAction("Сделать начальным", self)
        make_initial_action.triggered.connect(lambda: self.set_initial_node(node))

        actions = [delete_action, edit_action, make_initial_action]

        if len(selected_nodes) == 0 or len(selected_nodes) == 1:
            if not node.has_loop():
                make_loop_action = QAction("Сделать петлю", self)
                make_loop_action.triggered.connect(lambda: self.create_edge(node, node))
                actions.append(make_loop_action)
            return actions

        src: Node = (
            selected_nodes[0] if selected_nodes[0] is not node else selected_nodes[1]
        )
        if src.name not in node.in_edges:
            add_edge_action = QAction("Соединить", self)
            add_edge_action.triggered.connect(lambda: self.create_edge(src, node))
            actions.append(add_edge_action)

        return actions

    def edge_actions(self, edge: Edge) -> list[QAction]:
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
            edge.add_transition(in_, out_)

        delete_action = QAction("Удалить", self)
        edit_action = QAction("Редактировать", self)
        add_action = QAction("Добавить", self)

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
            node.out_edges.pop(node.name)
            self.removeItem(edge)
            del edge

        for src_node in list(node.in_edges.keys()):
            # Удаляем текущий узел (приемник)
            # из списка ребер узла, из которого оно исходит
            edge = node.in_edges.pop(src_node)
            edge.source.out_edges.pop(node.name)

            # Удаляем само реберо
            self.removeItem(edge)
            del edge

        for dst_node in list(node.out_edges.keys()):
            # Удаляем текущий узел (источник)
            # из списка ребер узла, в которое ребро входит
            edge = node.out_edges.pop(dst_node)
            edge.destination.in_edges.pop(node.name)

            self.removeItem(edge)
            del edge

        # Удаляем узел реберо
        self.nodes.pop(node.name)
        self.removeItem(node)
        del node

    def delete_edge(self, edge: Edge) -> None:
        edge.source.out_edges.pop(edge.destination.name)
        edge.destination.in_edges.pop(edge.source.name)
        self.removeItem(edge)
        del edge

    def set_initial_node(self, node: Node) -> Node:
        color = QColor(128, 25, 90, 180)  # Standard purple color
        if self.initial_state:
            self.initial_state.setBrush(QBrush(node.NODE_COLOR))
        self.initial_state = node
        node.setBrush(QBrush(color))

    @staticmethod
    def enter_edge() -> list[str]:
        input_field = VerticalInputDialog("Вход", "Выход:")
        return input_field.get_values()

    def mark_node(self, node_name: str, color: QColor) -> None:
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
        brush.setColor(node.NO)
        node.setBrush(brush)

        if node in self.marked_nodes_:
            self.marked_nodes_.remove(node)

    def serialize(self) -> str:
        initial_state = ""
        if self.initial_state:
            initial_state = self.initial_state.name
        return {
            "nodes": [node.serialize() for node in self.nodes.values()],
            "edges": [edge.serialize() for edge in self.edges],
            "initial_state": initial_state,
        }

    def deserialize(self, json_str: str) -> None:
        data = json.loads(json_str)

        # Восстановить узлы по именам
        self.nodes = {}
        for node_data in data["nodes"]:
            node = Node.deserialize(node_data)
            self.nodes[node.name] = node
            self.addItem(node)

        # Восстановить ребра
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


class AutomataGraphView(QGraphicsView):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.scene_ = AutomataDrawScene(self)
        self.setScene(self.scene_)
        self.setWhatsThis("Это описание данного виджета или кнопки.")

        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.TextAntialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.viewport().setCursor(Qt.CursorShape.ArrowCursor)

    @property
    def marked_nodes(self) -> list[str]:
        return self.scene_.marked_nodes_

    def mousePressEvent(self, event: QMouseEvent | None) -> None:
        super().mousePressEvent(event)
        # После начала перетаскивания вернуть курсор стрелки
        self.viewport().setCursor(Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self, event: QMouseEvent | None) -> None:
        super().mouseReleaseEvent(event)
        # После отпускания кнопки вернуть курсор стрелки
        self.viewport().setCursor(Qt.CursorShape.ArrowCursor)

    def mouseDoubleClickEvent(self, event: QMouseEvent | None) -> None:
        super().mouseDoubleClickEvent(event)
        self.viewport().setCursor(Qt.CursorShape.ArrowCursor)

    def wheelEvent(self, event: QWheelEvent | None) -> None:
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            zoom_direction = event.angleDelta().y() > 0
            self.zoom_scene(zoom_direction, event.position())
        return super().wheelEvent(event)

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

    def mark_node(self, node_name: str, color: QColor) -> None:
        self.scene_.mark_node(node_name, color)

    def unmark_node(self, node_name: str) -> None:
        self.scene_.unmark_node(node_name)

    def load_scene(self, json_str: str) -> None:
        self.scene_.deserialize(json_str)

    def dump_scene(self) -> None:
        return self.scene_.serialize()

    def to_automata(self) -> Automata:
        initial_state = ""
        if self.scene_.initial_state:
            initial_state = self.scene_.initial_state.name
        automata = Automata(list(self.nodes.keys()), initial_state)
        for name, node in self.nodes.items():
            for dest_name, edge in node.out_edges.items():
                for in_ in edge.inputs():
                    for out_ in edge.output(in_):
                        automata.add_input(in_)
                        automata.add_output(out_)
                        automata.add_transition(in_, name, dest_name, out_)

        automata.reset_input_order(sorted(automata.input_alphabet))
        automata.reset_output_order(sorted(automata.output_alphabet))
        return automata

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
