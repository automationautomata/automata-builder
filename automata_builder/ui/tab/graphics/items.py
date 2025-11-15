import copy
import math
from typing import Any, Optional

import PyQt6.QtGui as qtg
import PyQt6.QtWidgets as qtw
from PyQt6.QtCore import QPointF, Qt

from ..common import EditableTextItem


class Node(qtw.QGraphicsEllipseItem):
    COLOR = Qt.GlobalColor.cyan
    FONT = qtg.QFont("Arial", 11)

    def __init__(
        self, name: str, x: int | float, y: int | float, radius: int | float = 20
    ) -> None:
        super().__init__(-radius, -radius, 2 * radius, 2 * radius)
        self._name = name
        self.in_edges: dict[str, Edge] = {}  # ребра, входящие в узел
        self.out_edges: dict[str, Edge] = {}  # ребра, исходящие из узла

        self.setBrush(qtg.QBrush(self.COLOR))
        self.setPen(qtg.QPen(Qt.GlobalColor.black))
        self.setFlag(
            self.GraphicsItemFlag.ItemIsMovable
            | self.GraphicsItemFlag.ItemIsSelectable
            | self.GraphicsItemFlag.ItemSendsScenePositionChanges
        )
        self.setPos(x, y)

        self.name_text_item = EditableTextItem(self._name, self)
        self.name_text_item.setFont(self.FONT)
        self.name_text_item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.name_text_item.setFlag(
            qtw.QGraphicsTextItem.GraphicsItemFlag.ItemIsFocusable, False
        )

        doc = self.name_text_item.document()
        doc.setDocumentMargin(0)  # Убирает отступы вокруг текста

        text_rect = self.name_text_item.boundingRect()
        center = self.rect().center()
        self.name_text_item.setPos(
            center.x() - text_rect.width() / 2, center.y() - text_rect.height() / 2
        )

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value
        self.name_text_item.setPlainText(value)

    def enable_name_edit(self) -> None:
        self.name_text_item.enable_edit()

    def disable_name_edit(self) -> None:
        self._name = self.name_text_item.toPlainText()
        self.name_text_item.disable_edit()

    def has_loop(self) -> bool:
        return self._name in self.in_edges

    def itemChange(self, change, value) -> Any:
        if change == self.GraphicsItemChange.ItemPositionHasChanged:
            for edge in self.in_edges.values():
                edge.update_path()
            for edge in self.out_edges.values():
                edge.update_path()
        return super().itemChange(change, value)

    def serialize(self) -> dict[str, Any]:
        return {
            "name": self._name,
            "x": self.pos().x(),
            "y": self.pos().y(),
            "radius": self.rect().width() / 2,
        }

    @staticmethod
    def deserialize(data: dict) -> "Node":
        node = Node(
            name=data["name"],
            x=data["x"],
            y=data["y"],
            radius=data.get("radius", 20),
        )
        return node


class Edge(qtw.QGraphicsPathItem):
    TEXT_COLOR = Qt.GlobalColor.red
    BASIC_COLOR = Qt.GlobalColor.black
    SELECTED_COLOR = Qt.GlobalColor.red
    TEXT_FONT = qtg.QFont("Arial", 14)

    def __init__(
        self,
        input_value: str,
        output_value: str,
        source: Node,
        destination: Node,
        click_area_size: int = 10,
    ) -> None:
        super().__init__()
        # each input could have only one output
        self.transitions = {output_value: [input_value]}

        self.source = source
        self.destination = destination
        self.is_reversed = self.destination.name in self.source.in_edges
        self.setPen(qtg.QPen(self.BASIC_COLOR, 2))
        self.setFlag(
            self.GraphicsItemFlag.ItemIsSelectable
            | self.GraphicsItemFlag.ItemSendsScenePositionChanges
        )

        self.text_item: EditableTextItem = None
        self.arrow_head: qtw.QGraphicsPolygonItem = None

        self.arrow_size_ = 10
        self.bend_ratio_ = 0.5  # from 0 to 1, 0 — source, 1 — destination
        self.bend_offset_ = 5.0
        self.click_area_size_ = click_area_size
        self.dragging_control_point_ = False

    def isloop(self):
        return self.destination is self.source

    @property
    def edge_text(self) -> str:
        return ", ".join(
            f"{','.join(inputs)} | {output}"
            for output, inputs in self.transitions.items()
        )

    def input(self, output_value: str) -> set[str]:
        if output_value not in self.transitions:
            raise KeyError("Input value not in input-output table")
        return self.transitions[output_value].copy()

    def outputs(self) -> list[str]:
        return list(self.transitions.keys())

    def has_in_transitions(self, input_value: str, output_value: str) -> bool:
        if input_value not in self.transitions:
            return False
        return output_value in self.transitions[input_value]

    def add_transition(self, output_value: str, input_value: str) -> None:
        if output_value not in self.transitions:
            self.transitions[output_value] = []
        elif input_value in self.transitions[output_value]:
            return

        self.transitions[output_value].append(input_value)
        if not self.text_item:
            return

        font = self.text_item.font()
        if font.pointSizeF() > 9:
            font.setPointSizeF(font.pointSizeF() - 0.12)
            self.text_item.setFont(font)

        self.text_item.setPlainText(self.edge_text)

    def remove_transition(self, input_value: str, output_value: str) -> None:
        if input_value not in self.transitions:
            raise ValueError()
        if output_value in self.transitions[input_value]:
            raise ValueError()

        self.transitions[input_value].remove(output_value)
        if len(self.transitions[input_value]) == 0:
            del self.transitions[input_value]

    def shape(self) -> qtg.QPainterPath:
        original_path = super().shape()
        stroker = qtg.QPainterPathStroker()

        stroker.setWidth(self.click_area_size_ * 2)
        expanded_path = stroker.createStroke(original_path)
        # Создаем новую область с заданной шириной вокруг исходного пути
        return expanded_path

    def paint(self, painter, option, widget=None):
        # Переопределяем метод рисования
        option.state &= ~qtw.QStyle.StateFlag.State_Selected
        super().paint(painter, option, widget)

    def itemChange(
        self, change: qtw.QGraphicsItem.GraphicsItemChange, value: Any
    ) -> Any:
        if change == self.GraphicsItemChange.ItemSelectedHasChanged:
            pen_width = self.pen().width()
            if value:
                pen = qtg.QPen(self.SELECTED_COLOR, pen_width)
            else:
                pen = qtg.QPen(self.BASIC_COLOR, pen_width)
            self.setPen(pen)
        return super().itemChange(change, value)

    def mouseDoubleClickEvent(
        self, event: Optional[qtw.QGraphicsSceneMouseEvent]
    ) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging_control_point_ = True
        return super().mousePressEvent(event)

    def mouseMoveEvent(self, event: Optional[qtw.QGraphicsSceneMouseEvent]):
        if self.dragging_control_point_:
            # Обновляем bend_ratio_ в зависимости от положения мыши относительно линии
            source_point = self.get_boundary_point(self.source, self.destination)
            dest_point = self.get_boundary_point(self.destination, self.source)

            line_vec = dest_point - source_point
            total_length = math.hypot(line_vec.x(), line_vec.y())

            if total_length == 0:
                return

            click_pos = event.scenePos()

            # Проекция точки на линию для определения ratio
            vec_to_click = click_pos - source_point
            ratio_along_line = (
                vec_to_click.x() * line_vec.x() + vec_to_click.y() * line_vec.y()
            ) / (total_length**2)

            # Ограничиваем ratio между 0 и 1
            ratio_along_line_clamped = 1.0 - max(0.0, min(1.0, ratio_along_line))
            self.bend_ratio_ = ratio_along_line_clamped

            # Расчет нового bend_offset_ как расстояния от точки до линии вдоль перпендикуляра
            mid_point_new = source_point + line_vec * self.bend_ratio_
            perp_vector = QPointF(-line_vec.y(), line_vec.x()) / total_length

            # Проекция точки на линию для определения offset
            vec_to_click_new = click_pos - mid_point_new
            bend_offset__new = (
                qtg.QVector2D(vec_to_click_new).toPointF().x() * perp_vector.x()
                + qtg.QVector2D(vec_to_click_new).toPointF().y() * perp_vector.y()
            )

            # Можно ограничить или оставить без ограничений
            self.bend_offset_ = bend_offset__new
            # Обновляем путь с новым изгибом
            self.update_path()

        return super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: Optional[qtw.QGraphicsSceneMouseEvent]):
        self.dragging_control_point_ = False
        return super().mouseReleaseEvent(event)

    def update_path(self) -> None:
        path = qtg.QPainterPath()

        if self.isloop():
            rect = self.source.rect()
            top_center = self.source.mapToScene(QPointF(rect.center().x(), rect.top()))
            path.moveTo(top_center)

            x_offset, y_offset = 40, 50
            ctrlPt1 = QPointF(top_center.x() - x_offset, top_center.y() - y_offset)
            ctrlPt2 = QPointF(top_center.x() + x_offset, top_center.y() - y_offset)

            path.cubicTo(ctrlPt2, ctrlPt1, top_center)
        else:
            source_point = self.get_boundary_point(self.source, self.destination)
            dest_point = self.get_boundary_point(self.destination, self.source)
            control_point = self.get_control_point(
                source_point, dest_point, self.bend_ratio_, self.bend_offset_
            )
            path.moveTo(source_point)
            path.quadTo(control_point, dest_point)

        self.setPath(path)
        self.draw_arrowhead()
        self.draw_edge_text()

    @staticmethod
    def get_control_point(
        dest_point: QPointF,
        source_point: QPointF,
        bend_ratio_: float,
        bend_offset_: float,
    ) -> QPointF:
        line_vec = dest_point - source_point
        length = math.hypot(line_vec.x(), line_vec.y())

        if length == 0:
            return source_point

        # Точка на линии по bend_ratio_
        bend_point = source_point + line_vec * bend_ratio_

        # Перпендикуляр к линии
        perp = QPointF(line_vec.y(), -line_vec.x()) / length

        # Смещение по перпендикуляру на bend_offset_
        return bend_point + perp * bend_offset_

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

    def draw_edge_text(self) -> None:
        if not self.text_item:
            self.text_item = EditableTextItem(self.edge_text, self)
            self.text_item.setFlag(self.GraphicsItemFlag.ItemSendsScenePositionChanges)
            self.text_item.setFlag(self.GraphicsItemFlag.ItemIsSelectable, False)
            self.text_item.setFlag(self.GraphicsItemFlag.ItemIsFocusable, False)
            self.text_item.setDefaultTextColor(Qt.GlobalColor.red)
            self.text_item.setFont(self.TEXT_FONT)
            self.text_item.setPlainText(self.edge_text)
            scene = self.scene()
            if scene:
                scene.addItem(self.text_item)

        if self.isloop():
            bend_point = self.path().pointAtPercent(0.5)
        else:
            ratio = max(0.25, min(self.bend_ratio_, 0.75))
            bend_point = self.path().pointAtPercent(1 - ratio)

        line_vec = self.path().pointAtPercent(0.75) - self.path().pointAtPercent(0.25)
        line_length = math.hypot(line_vec.x(), line_vec.y())

        if line_length <= 0:
            return
        unit_vector = QPointF(line_vec.x() / line_length, line_vec.y() / line_length)
        perp_vector = QPointF(-unit_vector.y(), unit_vector.x())

        perp_offset = 10 if not self.isloop() else 22
        self.text_item.setPos(bend_point + perp_vector * perp_offset)

        angle = math.degrees(math.atan2(unit_vector.y(), unit_vector.x())) % 2 * math.pi
        self.text_item.setRotation(angle)

    def draw_arrowhead(self) -> None:
        # Удаляем старый стрелочный элемент, если есть
        if self.arrow_head:
            scene = self.scene()
            if scene:
                scene.removeItem(self.arrow_head)
            del self.arrow_head

        path_length = self.path().length()
        if path_length == 0:
            return

        # Получаем точку на конце кривой (конец линии)
        end_point = self.path().pointAtPercent(1.0)

        # Получаем точку чуть перед конца для определения направления стрелки
        # Можно взять чуть назад по линии для определения направления стрелки
        tail_percent = max(0.0, 1.0 - self.arrow_size_ / path_length)
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
            - unit_vector * self.arrow_size_
            + perp_vector * (self.arrow_size_ / 2)
        )
        point3 = (
            end_point
            - unit_vector * self.arrow_size_
            - perp_vector * (self.arrow_size_ / 2)
        )

        arrow_polygon = qtg.QPolygonF([point1, point2, point3])

        arrow_item = qtw.QGraphicsPolygonItem(arrow_polygon, self)
        arrow_item.setBrush(Qt.GlobalColor.black)
        arrow_item.setPen(qtg.QPen(Qt.GlobalColor.black))

        # Save reference to remove later if needed
        self.arrow_head = arrow_item

    def serialize(self) -> dict[str, Any]:
        return {
            "source": self.source.name,
            "destination": self.destination.name,
            "transitions": self.transitions,
            "bend_ratio": self.bend_ratio_,
            "bend_offset": self.bend_offset_,
        }

    @staticmethod
    def deserialize(data: dict, nodes: dict[str, Node]) -> "Edge":
        source = nodes[data["source"]]
        dest = nodes[data["destination"]]
        transitions = data["transitions"]

        edge = Edge("", "", source, dest)
        edge.bend_ratio_ = data["bend_ratio"]
        edge.bend_offset_ = data["bend_offset"]
        edge.transitions = copy.deepcopy(transitions)
        source.out_edges[dest.name] = edge
        dest.in_edges[source.name] = edge
        return edge
