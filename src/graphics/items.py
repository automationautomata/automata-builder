import copy
import math
from typing import Any

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import (
    QBrush,
    QFont,
    QPainterPath,
    QPainterPathStroker,
    QPen,
    QPolygonF,
)
from PyQt6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsPathItem,
    QGraphicsPolygonItem,
    QGraphicsSceneMouseEvent,
    QGraphicsTextItem,
)

from widgets import (
    EditableTextItem,
)


class Node(QGraphicsEllipseItem):
    NODE_COLOR = Qt.GlobalColor.cyan

    def __init__(
        self, name: str, x: int | float, y: int | float, radius: int | float = 20
    ) -> None:
        super().__init__(-radius, -radius, 2 * radius, 2 * radius)
        self.name = name
        self.in_edges: dict[str, Edge] = {}  # ребра, входящие в узел
        self.out_edges: dict[str, Edge] = {}  # ребра, исходящие из узла

        self.setBrush(QBrush(self.NODE_COLOR))
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

    def has_loop(self) -> bool:
        return self.name in self.in_edges

    def itemChange(self, change, value) -> Any:
        if change == self.GraphicsItemChange.ItemPositionHasChanged:
            for edge in self.in_edges.values():
                edge.update_path()
            for edge in self.out_edges.values():
                edge.update_path()
        return super().itemChange(change, value)

    def serialize(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "x": self.pos().x(),
            "y": self.pos().y(),
            "radius": self.rect().width() / 2,
        }

    @staticmethod
    def deserialize(data: dict) -> "Node":
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

    def has_transition(self, input_value: str, output_value: str) -> bool:
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

    def serialize(self) -> dict[str, Any]:
        return {
            "transitions": self.transitions,  # первый ключ или по необходимости
            "source": self.source.name,
            "destination": self.destination.name,
        }

    @staticmethod
    def deserialize(data: dict, nodes: dict[str, Node]) -> "Edge":
        source = nodes[data["source"]]
        dest = nodes[data["destination"]]
        transitions = data["transitions"]

        edge = Edge("", "", source, dest)
        edge.transitions = copy.deepcopy(transitions)
        source.out_edges[dest.name] = edge
        dest.in_edges[source.name] = edge
        return edge
