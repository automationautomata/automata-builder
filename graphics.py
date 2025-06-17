import json
import math
from typing import Any

from PyQt6.QtCore import QPoint, QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QFont,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPainterPathStroker,
    QPen,
    QPolygonF,
    QWheelEvent,
)
from PyQt6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsPathItem,
    QGraphicsPolygonItem,
    QGraphicsScene,
    QGraphicsSceneMouseEvent,
    QGraphicsTextItem,
    QGraphicsView,
    QMenu,
    QMessageBox,
    QPushButton,
    QWidget,
)

from automata import Automata
from tools.utiles import save_view
from tools.widgets import (
    EditableTextItem,
    TableInputDialog,
    VerticalInputDialog,
)


class Node(QGraphicsEllipseItem):
    def __init__(
        self, name: str, x: int | float, y: int | float, radius: int | float = 20
    ) -> None:
        super().__init__(-radius, -radius, 2 * radius, 2 * radius)
        self.name = name
        self.in_edges: dict[str, Edge] = {}  # ребра, входящие в узел
        self.out_edges: dict[str, Edge] = {}  # ребра, исходящие из узла

        self.setBrush(QBrush(Qt.GlobalColor.cyan))
        self.setPen(QPen(Qt.GlobalColor.black))
        self.setFlag(
            QGraphicsEllipseItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsEllipseItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsEllipseItem.GraphicsItemFlag.ItemSendsScenePositionChanges
        )
        self.setPos(x, y)

        self.name_text_item = QGraphicsTextItem(self.name, self)
        self.name_text_item.setFont(QFont("Arial", 11))

        doc = self.name_text_item.document()
        doc.setDocumentMargin(0)  # Убирает отступы вокруг текста

        text_rect = self.name_text_item.boundingRect()
        center = self.rect().center()
        self.name_text_item.setPos(
            center.x() - text_rect.width() / 2, center.y() - text_rect.height() / 2
        )

    def has_loop(self):
        return self.name in self.in_edges

    def itemChange(self, change, value) -> Any:
        if change == self.GraphicsItemChange.ItemPositionHasChanged:
            for edge in self.in_edges.values():
                edge.update_path()
            for edge in self.out_edges.values():
                edge.update_path()
        return super().itemChange(change, value)

    def serialize(self):
        return {
            "name": self.name,
            "x": self.pos().x(),
            "y": self.pos().y(),
            "radius": self.rect().width() / 2,
        }

    @staticmethod
    def deserialize(data: dict):
        node = Node(
            name=data["name"], x=data["x"], y=data["y"], radius=data.get("radius", 20)
        )
        return node


class Edge(QGraphicsPathItem):
    def __init__(
        self, input_value: str, output_value: str, source: Node, destination: Node
    ) -> None:
        super().__init__()
        self.transitions = {input_value: [output_value]}

        self.source = source
        self.destination = destination
        self.is_reversed = self.destination.name in self.source.in_edges
        self.text_font = QFont("Arial", 14)
        self.setPen(QPen(Qt.GlobalColor.black, 2))
        self.setFlag(
            QGraphicsEllipseItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsEllipseItem.GraphicsItemFlag.ItemSendsScenePositionChanges
        )
        self.arrow_size = 10
        self.arrow_head = None
        self.text_item: EditableTextItem = None

        self.create_click_area(30)

    @property
    def edge_text(self) -> str:
        return ", ".join(
            f"{input_} | {','.join(outputs)}"
            for input_, outputs in self.transitions.items()
        )

    def inputs(self) -> set[str]:
        return set(self.transitions)

    def output(self, input_value: str) -> list[str]:
        if input_value not in self.transitions:
            raise KeyError("Input value not in input-output table")
        return self.transitions[input_value]

    def has_transition(self, input_value: str, output_value: str):
        if input_value not in self.transitions:
            return False
        return output_value in self.transitions[input_value]

    def add_transition(self, input_value: str, output_value: str) -> None:
        if input_value not in self.transitions:
            self.transitions[input_value] = []
        elif output_value in self.transitions[input_value]:
            return

        self.transitions[input_value].append(output_value)
        if not self.text_item:
            return

        font_size = self.text_font.pointSizeF()
        if font_size <= 0:
            font_size = self.text_font.pointSize()

        self.text_font.setPointSizeF(font_size - 0.12)
        self.text_item.setFont(self.text_font)
        self.text_item.setPlainText(self.edge_text)

    def remove_transition(self, input_value: str, output_value: str) -> None:
        if input_value not in self.transitions:
            raise ValueError()
        if output_value in self.transitions[input_value]:
            raise ValueError()

        self.transitions[input_value].remove(output_value)
        if len(self.transitions[input_value]) == 0:
            del self.transitions[input_value]

    def create_click_area(self, width: int) -> None:
        # Создаем новую область с шириной 'width' вокруг исходного пути
        stroker = QPainterPathStroker()
        stroker.setWidth(width)
        self.click_area = stroker.createStroke(self.path())

    def update_path(self) -> None:
        path = QPainterPath()

        if self.source is self.destination:
            rect = self.source.rect()
            top_center = self.source.mapToScene(QPointF(rect.center().x(), rect.top()))
            path.moveTo(top_center)

            x_offset, y_offset = 40, 50
            ctrlPt1 = QPointF(top_center.x() - x_offset, top_center.y() - y_offset)
            ctrlPt2 = QPointF(top_center.x() + x_offset, top_center.y() - y_offset)

            path.cubicTo(ctrlPt2, ctrlPt1, top_center)
        else:
            # Получаем позиции узлов
            source_point = self.get_boundary_point(self.source, self.destination)
            dest_point = self.get_boundary_point(self.destination, self.source)
            path.moveTo(source_point)
            # Создаем кривую с помощью quadTo (квадратичная кривая)
            # Можно выбрать контрольную точку для изгиба
            control_point = (source_point + dest_point) / 2

            if self.is_reversed:
                # смещение вниз
                control_point.setY(control_point.y() + 80)
            else:
                # смещение вверх
                control_point.setY(control_point.y() - 80)
            path.quadTo(control_point, dest_point)

        self.setPath(path)
        self.draw_arrowhead()
        self.create_edge_text()

    @staticmethod
    def get_boundary_point(source: Node, destination: Node) -> QPointF:
        # Центры узлов
        source_center = source.scenePos() + source.rect().center()
        dest_center = destination.scenePos() + destination.rect().center()

        # Вектор направления
        line_vec = dest_center - source_center
        angle = math.atan2(line_vec.y(), line_vec.x())

        # Размеры узлов
        rect = source.rect()
        width = rect.width() / 2
        height = rect.height() / 2

        # Для эллипса: найти точку на границе по углу
        # Формула для эллипса:
        # x = width * cos(t), y = height * sin(t)
        # где t - угол
        t = angle
        boundary_x = width * math.cos(t)
        boundary_y = height * math.sin(t)

        boundary_point_local = QPointF(boundary_x, boundary_y)
        boundary_point_scene = source_center + boundary_point_local

        return boundary_point_scene

    def create_edge_text(self) -> None:
        mid_point = self.path().pointAtPercent(0.5)
        offset = QPointF(0, -25)
        if self.text_item:  # and self.output_text_item and self.separator_text_item:
            self.text_item.setPos(mid_point + offset)
            return

        # Находим середину линии для отображения веса

        # Текстовый элемент для входа
        text_item = EditableTextItem(self.edge_text, self)
        text_item.setFlag(
            QGraphicsEllipseItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsEllipseItem.GraphicsItemFlag.ItemSendsScenePositionChanges
        )
        text_item.setDefaultTextColor(Qt.GlobalColor.red)
        text_item.setFont(self.text_font)
        text_item.setPos(mid_point + offset)

        scene = self.scene()
        if scene:
            scene.addItem(text_item)
            self.text_item = text_item

    def draw_arrowhead(self) -> None:
        # Удаляем старый стрелочный элемент, если есть
        if self.arrow_head:
            scene = self.scene()
            if scene:
                scene.removeItem(self.arrow_head)

        path_length = self.path().length()

        if path_length == 0:
            return

        # Получаем точку на конце кривой (конец линии)
        end_point = self.path().pointAtPercent(1.0)

        # Получаем точку чуть перед конца для определения направления стрелки
        # Можно взять чуть назад по линии для определения направления стрелки
        tail_percent = max(0.0, 1.0 - self.arrow_size / path_length)
        start_arrow_point = self.path().pointAtPercent(tail_percent)

        # Вектор направления стрелки (от start к end)
        direction_vector = end_point - start_arrow_point

        # Нормализуем вектор и масштабируем до размера стрелки
        length = math.hypot(direction_vector.x(), direction_vector.y())
        if length == 0:
            return

        unit_vector = QPointF(
            direction_vector.x() / length,
            direction_vector.y() / length,
        )

        # Перпендикуляр к вектору для создания треугольника стрелки
        perp_vector = QPointF(-unit_vector.y(), unit_vector.x())

        # Точки треугольника стрелки относительно конца линии
        point1 = end_point
        point2 = (
            end_point
            - unit_vector * self.arrow_size
            + perp_vector * (self.arrow_size / 2)
        )
        point3 = (
            end_point
            - unit_vector * self.arrow_size
            - perp_vector * (self.arrow_size / 2)
        )

        arrow_polygon = QPolygonF([point1, point2, point3])

        arrow_item = QGraphicsPolygonItem(arrow_polygon, self)
        arrow_item.setBrush(Qt.GlobalColor.black)
        arrow_item.setPen(QPen(Qt.GlobalColor.black))

        scene = self.scene()
        if scene:
            scene.addItem(arrow_item)

        # Save reference to remove later if needed
        self.arrow_head = arrow_item

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if event.button() == Qt.MouseButton.RightButton:
            pass

    def serialize(self):
        return {
            "transitions": self.transitions,  # первый ключ или по необходимости
            "source": self.source.name,
            "destination": self.destination.name,
        }

    @staticmethod
    def deserialize(data: dict, nodes: dict):
        source = nodes[data["source"]]
        dest = nodes[data["destination"]]
        transitions = data["transitions"]

        edge = Edge("", "", source, dest)
        edge.__dict__["transitions"] = transitions
        return edge


class EdgeEditDialog(TableInputDialog):
    def __init__(self, edge: Edge, title="") -> None:
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
        if not values:
            return None

        for i in range(len(values)):
            if not values[i][0]:
                values[i][0] = self.transitions[i][0]

            if not values[i][1]:
                values[i][1] = self.transitions[i][1]

        return values


class AutomataGraphView(QGraphicsView):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.fitInView(
            QRectF(0, 0, self.height() / 5, self.width() / 5),
            Qt.AspectRatioMode.KeepAspectRatio,
        )
        self.setWhatsThis("Это описание данного виджета или кнопки.")

        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.TextAntialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.customContextMenuRequested.connect(self.context_menu)
        self.initial_state: Node = None

        self.nodes: dict[str, Node] = {}  # словарь имя-узел
        self.edges: list[Edge] = []
        self.selected_nodes: list[Node] = []  # выделенные узлы для соединения
        self.viewport().setCursor(Qt.CursorShape.ArrowCursor)

    def mousePressEvent(self, event: QMouseEvent | None) -> None:
        super().mousePressEvent(event)
        # После начала перетаскивания вернуть курсор стрелки
        self.viewport().setCursor(Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self, event: QMouseEvent | None) -> None:
        super().mouseReleaseEvent(event)
        # После отпускания кнопки вернуть курсор стрелки
        self.viewport().setCursor(Qt.CursorShape.ArrowCursor)

    def mouseDoubleClickEvent(self, event: QMouseEvent | None) -> None:
        scene_pos = self.mapToScene(event.position().toPoint())
        items = self.scene().items(scene_pos)
        if len(items) == 0:
            # Клик по пустому месту — добавляем новый узел в место клика
            name = f"S{len(self.nodes)}"
            new_node = Node(name, scene_pos.x(), scene_pos.y())
            self.scene().addItem(new_node)
            self.nodes[name] = new_node
        super().mouseDoubleClickEvent(event)
        self.viewport().setCursor(Qt.CursorShape.ArrowCursor)

    def wheelEvent(self, event: QWheelEvent | None) -> None:
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            zoom_direction = event.angleDelta().y() > 0
            self.zoom_scene(zoom_direction, event.position())
        return super().wheelEvent(event)

    def keyPressEvent(self, event: QKeyEvent | None):
        is_s_key = event.key() == Qt.Key.Key_S
        is_cntrl_modifier = event.modifiers() == Qt.KeyboardModifier.ControlModifier

        if is_cntrl_modifier and is_s_key:
            self.save_to_file()

        return super().keyPressEvent(event)

    def context_menu(self, point: QPoint) -> None:
        items = self.scene().items(self.mapToScene(point))
        if len(items) != 1:
            return
        item = items[0]
        menu = QMenu(self)

        # Add actions to the menu
        if isinstance(item, Node):
            menu.addActions(self.node_actions(item))
        elif isinstance(item, Edge):
            menu.addActions(self.edge_actions(item))

        # Отображаем меню в позиции курсора
        action = menu.exec(self.mapToGlobal(point))
        # Можно проверить выбранное действие
        if action:
            print(f"Выбрано действие: {action.text()}")

    def node_actions(self, node: Node) -> list[QAction]:
        def delete_node():
            nonlocal node
            for in_node in list(node.in_edges.keys()):
                # Удаляем текущий узел (принимающий)
                # из ребер узла, из которого оно исходит
                edge = node.in_edges[in_node]
                edge.source.out_edges.pop(in_node)

                # Удаляем само реберо
                node.in_edges.pop(in_node)
                self.scene().removeItem(edge)

            for out_node in list(node.out_edges.keys()):
                # Удаляем текущий узел (источник)
                # из ребер узла, в которое ребро входит
                edge = node.out_edges[out_node]
                edge.destination.in_edges.pop(out_node)

                node.out_edges.pop(out_node)
                self.scene().removeItem(edge)

            # Удаляем узел реберо
            self.nodes.pop(node.name)
            self.scene().removeItem(node)
            del node

        def edit_node():
            old_name = node.name
            node.name_text_item.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextEditorInteraction
            )
            node.name_text_item.setFocus()

            new_name = node.name_text_item.toPlainText()
            if new_name != old_name and new_name in self.nodes:
                QMessageBox.warning(
                    self, "Ошибка", "Узел с таким названием уже существует"
                )
                return
            self.nodes.pop(old_name)
            self.nodes[new_name] = node

        def set_initial_node():
            color = QColor(128, 25, 90, 180)  # Standard purple color
            if self.initial_state:
                basic_color = node.brush().color()
                self.initial_state.setBrush(QBrush(basic_color))
            self.initial_state = node
            node.setBrush(QBrush(color))

        selected = [
            item for item in self.scene().selectedItems() if isinstance(item, Node)
        ]
        if len(selected) > 2:
            return []

        delete_action = QAction("Удалить", self)
        delete_action.triggered.connect(delete_node)

        edit_action = QAction("Редактировать", self)
        edit_action.triggered.connect(edit_node)

        make_initial_action = QAction("Сделать начальным", self)
        make_initial_action.triggered.connect(set_initial_node)

        actions = [delete_action, edit_action, make_initial_action]

        if len(selected) == 0 or len(selected) == 1:
            if not node.has_loop():
                make_loop_action = QAction("Сделать петлю", self)
                make_loop_action.triggered.connect(lambda: self.create_edge(node, node))
                actions.append(make_loop_action)
            return actions

        src: Node = selected[0] if selected[0] is not node else selected[1]
        if src.name not in node.in_edges:
            add_edge_action = QAction("Соединить", self)
            add_edge_action.triggered.connect(lambda: self.create_edge(src, node))
            actions.append(add_edge_action)

        return actions

    def edge_actions(self, edge: Edge) -> list[QAction]:
        def delete_edge():
            nonlocal edge
            edge.source.out_edges.pop(edge.destination.name)
            edge.destination.in_edges.pop(edge.source.name)
            self.scene().removeItem(edge)
            del edge

        def edit_edge():
            dialog = EdgeEditDialog(edge, "Редактирование")
            values = dialog.get_values()
            if not values:
                return

            edge.transitions = {}
            for in_, out_ in zip(*values):
                edge.add_transition(in_, out_)

        def new_transition():
            values = self.enter_edge()
            if not values or not (values[0] and values[1]):
                return
            in_, out_ = values
            edge.add_transition(in_, out_)

        delete_action = QAction("Удалить", self)
        edit_action = QAction("Редактировать", self)
        add_action = QAction("Добавить", self)

        delete_action.triggered.connect(delete_edge)
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

        self.scene().addItem(edge)
        edge.update_path()

    @staticmethod
    def enter_edge() -> list[str]:
        input_field = VerticalInputDialog("Вход", "Выход:")
        return input_field.get_values()

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

    def to_automata(self) -> Automata:
        automata = Automata(list(self.nodes.keys()), self.initial_state)
        for name, node in self.nodes.items():
            for dest_name, edge in node.out_edges.items():
                for in_ in edge.inputs():
                    for out_ in edge.output(in_):
                        automata.add_input_symbol(in_)
                        automata.add_output_symbol(out_)
                        automata.add_transition(in_, name, dest_name, out_)

        automata.reset_input_order(sorted(automata.input_alphabet))
        automata.reset_output_order(sorted(automata.output_alphabet))
        return automata

    def save_to_file(self) -> None:
        save_view(self.serialize())
        QMessageBox.information(self, "Notification", "saved")

    def serialize(self) -> str:
        return {
            "nodes": [node.serialize() for node in self.nodes.values()],
            "edges": [edge.serialize() for edge in self.edges],
        }

    @staticmethod
    def deserialize_graph(json_str: str) -> tuple[dict[str, Node], list[Edge]]:
        data = json.loads(json_str)

        # Восстановить узлы по именам
        nodes_dict = {}
        for node_data in data["nodes"]:
            node = Node.deserialize(node_data)
            nodes_dict[node.name] = node

        # Восстановить ребра
        edges_list = []
        for edge_data in data["edges"]:
            edge = Edge.deserialize(edge_data, nodes_dict)
            edges_list.append(edge)

        return nodes_dict, edges_list

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
