import math

from PyQt6.QtCore import QPoint, QPointF, Qt
from PyQt6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPainterPathStroker,
    QPen,
    QPolygonF,
    QMouseEvent,
)
from PyQt6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsPathItem,
    QGraphicsPolygonItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QMenu,
    QMessageBox,
    QGraphicsSceneMouseEvent,
    QWidget,
)

from automata import Automata
from tools import EditableTextItem, MultipleInputDialog


class Node(QGraphicsEllipseItem):
    def __init__(
        self, name: str, x: int | float, y: int | float, radius: int | float = 20
    ) -> None:
        super().__init__(-radius, -radius, 2 * radius, 2 * radius)
        self.name = name
        self.in_edges: dict[str, Edge] = {}  # ребра, исходящие из узла
        self.out_edges: dict[str, Edge] = {}  # ребра, исходящие из узла

        # self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.setBrush(QBrush(Qt.GlobalColor.cyan))
        self.setPen(QPen(Qt.GlobalColor.black))
        self.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(
            QGraphicsEllipseItem.GraphicsItemFlag.ItemSendsScenePositionChanges
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

    def itemChange(self, change, value) -> None:
        if change == self.GraphicsItemChange.ItemPositionHasChanged:
            for edge in self.in_edges.values():
                edge.update_path()
            for edge in self.out_edges.values():
                edge.update_path()
        return super().itemChange(change, value)


class Edge(QGraphicsPathItem):
    def __init__(
        self, input_value: str, output_value: str, source: Node, destination: Node
    ) -> None:
        super().__init__()
        self.input_output_table = {input_value: [output_value]}

        self.source = source
        self.destination = destination
        self.is_reversed = self.destination.name in self.source.in_edges
        self.text_font = QFont("Arial", 14)
        self.setPen(QPen(Qt.GlobalColor.black, 2))

        self.arrow_size = 10
        self.arrow_head = None
        self.text_item: EditableTextItem = None

        self.create_click_area(30)

    def create_click_area(self, width: int) -> None:
        # Создаем новую область с шириной 'width' вокруг исходного пути
        stroker = QPainterPathStroker()
        stroker.setWidth(width)
        self.click_area = stroker.createStroke(self.path())

    def inputs(self) -> set[str]:
        return set(self.input_output_table)

    def output(self, input_value: str) -> list[str]:
        return self.input_output_table[input_value]

    @property
    def edge_text(self) -> str:
        return ", ".join(
            f"{input_} | {','.join(outputs)}"
            for input_, outputs in self.input_output_table.items()
        )

    def add_transition(self, input_value: str, output_value: str) -> None:
        if input_value not in self.input_output_table:
            self.input_output_table[input_value] = []
        elif output_value in self.input_output_table[input_value]:
            return

        self.input_output_table[input_value].append(output_value)
        if self.text_item:
            self.text_font.setPointSizeF(self.text_font.pointSizeF() - 0.12)

            self.text_item.setFont(self.text_font)
            self.text_item.setPlainText(self.edge_text)

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


class AutomataGraphView(QGraphicsView):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setSceneRect(0, 0, 700, 500)
        self.setFixedSize(720, 520)
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.TextAntialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu)
        self.initial_state: Node = None

        self.nodes: dict[str, Node] = {}  # словарь имя-узел
        self.edges: list[Edge] = []
        self.selected_nodes: list[Node] = []  # выделенные узлы для соединения

    def mouseDoubleClickEvent(self, event: QMouseEvent | None) -> None:
        scene_pos = self.mapToScene(event.position().toPoint())
        items = self.scene().items(scene_pos)
        if len(items) == 0:
            # Клик по пустому месту — добавляем новый узел в место клика
            pos = event.position().toPoint()
            name = f"S{len(self.nodes)}"
            new_node = Node(name, pos.x(), pos.y())
            self.scene().addItem(new_node)
            self.nodes[name] = new_node
        return super().mouseDoubleClickEvent(event)

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
            for in_node in list(node.in_edges.keys()):
                self.scene().removeItem(node.in_edges[in_node])
                node.in_edges.pop(in_node)

            for out_node in list(node.out_edges.keys()):
                self.scene().removeItem(node.out_edges[out_node])
                node.out_edges.pop(out_node)

            self.nodes.pop(node.name)
            self.scene().removeItem(node)

        def edit_node():
            old_name = node.name
            node.name_text_item.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextEditorInteraction
            )
            node.name_text_item.setFocus()

            new_name = node.name_text_item.toPlainText()
            if new_name != old_name and new_name in self.nodes:
                QMessageBox.warning(self, "Узел с таким названием уже существует")
                return
            self.nodes.pop(old_name)
            self.nodes[new_name] = node

        def set_initial_node():
            color = QColor(128, 10, 90)  # Standard purple color
            if self.initial_state:
                basic_color = node.brush().color()
                self.initial_state.setBrush(QBrush(basic_color))
            self.initial_state = node
            node.setBrush(QBrush(color))

        delete_action = QAction("Удалить", self)
        edit_action = QAction("Редактировать", self)
        make_initial_action = QAction("Сделать начальным", self)

        delete_action.triggered.connect(delete_node)
        edit_action.triggered.connect(edit_node)
        make_initial_action.triggered.connect(set_initial_node)

        selected = [
            item for item in self.scene().selectedItems() if isinstance(item, Node)
        ]
        if len(selected) == 0 or len(selected) > 2:
            return [delete_action, edit_action, make_initial_action]

        if len(selected) == 1:
            make_loop_action = QAction("Сделать петлю", self)
            make_loop_action.triggered.connect(lambda: self.create_edge(node, node))
            return [delete_action, edit_action, make_initial_action, make_loop_action]

        src: Node = selected[0] if selected[0] is not node else selected[1]
        if src.name in node.in_edges:
            return [delete_action, edit_action, make_initial_action]

        add_edge_action = QAction("Соединить", self)
        add_edge_action.triggered.connect(lambda: self.create_edge(src, node))

        return [delete_action, edit_action, make_initial_action, add_edge_action]

    def edge_actions(self, edge: Edge) -> list[QAction]:
        def edit_edge():
            values = self.enter_edge()
            if not values or len(values) < 2:
                return
            edge.input_value, edge.output_value = values

        def delete_edge():
            edge.source.out_edges.pop(edge.destination.name)
            edge.destination.in_edges.pop(edge.source.name)
            self.scene().removeItem(edge)

        def new_transition():
            values = self.enter_edge()
            if not values or len(values) < 2:
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
        if not values or len(values) < 2:
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
    def enter_edge() -> None:
        input_field = MultipleInputDialog("Вход", "Выход:")
        return input_field.getValues()

    def to_automata(self) -> Automata:
        inputs, outputs = [], []
        for edge in self.edges:
            inputs.append(edge.input_value)
            outputs.append(edge.output_value)

        automata = Automata(
            list(self.nodes.keys()), self.initial_state, inputs, outputs
        )
        for name, node in self.nodes.items():
            for dest_name, edge in node.out_edges.items():
                for in_ in edge.inputs():
                    for out_ in edge.output(in_):
                        automata.add_transition(in_, name, dest_name, out_)

        return Automata
